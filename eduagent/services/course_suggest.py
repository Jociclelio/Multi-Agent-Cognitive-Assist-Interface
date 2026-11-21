"""Sugestão de matérias a partir de arquivos soltos na UI (fluxo "+Nova").

Fluxo (decisão de produto registrada em 21/11/2026):

1. A UI envia os arquivos ao ``POST /courses/suggestions``; os bytes ficam em
   **staging** no diretório de dados (``<user>/staging/<suggestion_id>/``).
2. O serviço extrai uma **amostra de texto** de cada arquivo (Docling, primeiras
   páginas — o objetivo é classificar, não indexar; a ingestão completa
   re-extrai o documento inteiro depois, pelo caminho normal do Curador).
3. Uma única chamada ao **modelo de visão do runtime configurado** (mesmo
   adaptador da tutoria, sem ``json_schema`` presumido — parse/validação locais
   obrigatórios, mapa §3.1) agrupa os arquivos em matérias propostas com
   título e tópicos.
4. Cada matéria proposta é persistida como rascunho ``pending`` em
   ``course_suggestions`` (migração 0008) e aparece no rail da UI como
   **"esperando aprovação"**. O estudante revisa no popup (título/tópicos
   editáveis, arquivos visualizáveis) e confirma — aí a matéria real é criada
   e a ingestão dos arquivos dispara pelo caminho normal — ou descarta.

Fail-closed: sem backend admitido, a sugestão recusa com erro tipado
(``MODEL_NOT_ADMITTED``) e a UI cai para a aba manual. Sem extrator
(Docling ausente), a análise degrada para nomes de arquivo — nunca falha
silenciosamente: a resposta registra ``sample_chars`` por arquivo.

Todos os valores numéricos abaixo são DEFAULTS DE ENSAIO a calibrar — não são
resultados medidos (mapa §3).
"""

from __future__ import annotations

import json
import mimetypes
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.policy import resolve_owned_path
from eduagent.services.model_adapter import NON_THINKING_SAMPLER, Sampler

DIAGNOSTIC = "eduagent/services/course_suggest.py"

#: Amostra: primeiras páginas extraídas por arquivo (default de ensaio).
SAMPLE_PAGES = 10

#: Teto de caracteres de texto enviados por arquivo ao modelo (ensaio).
SAMPLE_CHARS_PER_FILE = 1500

#: TTL do rascunho pendente (ensaio): após expirar, confirmar recusa 410.
TTL_HOURS = 24

#: Teto de arquivos por pedido de sugestão (ensaio; corpo HTTP tem teto próprio).
MAX_FILES_PER_REQUEST = 10

_INGEST_FN = Callable[[str, str, bytes, str], dict[str, Any]]


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parser local tolerante (mesmo contrato do Tutor, mapa §3.1): um único
    objeto JSON, cercas de código toleradas por robustez com runtimes que
    ignoram a instrução de formato."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[len("json") :]
        stripped = stripped.strip()
    if not stripped.startswith("{"):
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "resposta do modelo não é um objeto JSON (formato acordado)",
            diagnostic=DIAGNOSTIC,
        )
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"JSON inválido do modelo: {exc.msg} (posição {exc.pos})",
            diagnostic=DIAGNOSTIC,
        ) from exc
    if not isinstance(data, dict):
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "resposta do modelo não é um objeto",
            diagnostic=DIAGNOSTIC,
        )
    return data


def _guess_mime(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


@dataclass(frozen=True)
class SuggestLimits:
    """Limites de ensaio da sugestão (mapa §3: defaults a calibrar)."""

    sample_pages: int = SAMPLE_PAGES
    sample_chars_per_file: int = SAMPLE_CHARS_PER_FILE
    llm_timeout_s: float = 300.0
    ttl_hours: int = TTL_HOURS
    max_files: int = MAX_FILES_PER_REQUEST

    @classmethod
    def from_mapping(cls, config: dict[str, Any] | None) -> "SuggestLimits":
        section = (config or {}).get("course_suggest") or {}
        if not isinstance(section, dict):
            section = {}
        return cls(
            sample_pages=int(section.get("sample_pages", SAMPLE_PAGES)),
            sample_chars_per_file=int(
                section.get("sample_chars_per_file", SAMPLE_CHARS_PER_FILE)
            ),
            llm_timeout_s=float(section.get("timeout_s", 300.0)),
            ttl_hours=int(section.get("ttl_hours", TTL_HOURS)),
            max_files=int(section.get("max_files", MAX_FILES_PER_REQUEST)),
        )


class CourseSuggestionService:
    """Rascunhos de matérias propostas (``course_suggestions``, migração 0008)."""

    def __init__(
        self,
        store: Any,
        data_root: Path | str,
        *,
        extractor: Any | None = None,
        backend: Any | None = None,
        limits: SuggestLimits | None = None,
        clock: Callable[[], datetime] | None = None,
        sampler: Sampler | None = None,
    ) -> None:
        self._store = store
        self._root = Path(data_root)
        self._extractor = extractor
        self._backend = backend
        self._limits = limits or SuggestLimits()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sampler = sampler or NON_THINKING_SAMPLER

    # -- staging ---------------------------------------------------------

    def _staging_dir(self, user_id: str, suggestion_id: str) -> Path:
        """Diretório de staging confinado ao dono (§15.1)."""
        return resolve_owned_path(
            self._root, user_id, f"staging/{suggestion_id}"
        )

    # -- análise (amostra + modelo) ---------------------------------------

    def _extract_sample(self, filename: str, raw: bytes) -> str:
        """Amostra de texto do arquivo; sem extrator → string vazia (a análise
        degrada para o nome do arquivo, registrado na resposta)."""
        if self._extractor is None or not raw:
            return ""
        try:
            extracted = self._extractor.extract(
                raw,
                _guess_mime(filename),
                max_pages=self._limits.sample_pages,
            )
        except EduAgentError:
            return ""
        chunks: list[str] = []
        budget = self._limits.sample_chars_per_file
        for page in extracted.pages:
            for block in page.blocks:
                text = (block.text or "").strip()
                if not text:
                    continue
                chunks.append(text)
                budget -= len(text)
                if budget <= 0:
                    break
            if budget <= 0:
                break
        return "\n".join(chunks)[: self._limits.sample_chars_per_file]

    def _call_model(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Uma chamada ao modelo de visão do runtime configurado; valida o
        objeto localmente (parse/schema obrigatórios SEMPRE, mapa §3.1)."""
        if self._backend is None:
            raise EduAgentError(
                ErrorCode.MODEL_NOT_ADMITTED,
                "sugestão de matérias exige modelo admitido (mapa §3.1); "
                "use a aba manual do popup",
                diagnostic=DIAGNOSTIC,
            )
        file_sections: list[str] = []
        for idx, entry in enumerate(entries, start=1):
            sample = entry["sample"] or "(sem texto extraído — classifique "
            "pelo nome do arquivo)"
            file_sections.append(
                f"[ARQUIVO {idx}] {entry['filename']}\n{sample}"
            )
        prompt = (
            "Você agrupa materiais de estudo em matérias (disciplinas).\n"
            "Para cada arquivo você recebe o nome e uma amostra do início do "
            "conteúdo.\n\n"
            "Responda com UM ÚNICO objeto JSON (sem cercas de código), no "
            "formato exato:\n"
            '{"courses": [{"title": "<nome da matéria>", "topics": '
            '["<tópico>", ...]}], "assignments": [{"file": <índice do '
            '"arquivo", int>, "course": <índice da matéria, int>}]}'
            "\n\nRegras: agrupe arquivos da MESMA matéria juntos; crie quantas "
            "matérias forem detectadas (pode ser uma só); títulos e tópicos "
            "em português; 3 a 8 tópicos por matéria.\n\n"
            "Arquivos:\n" + "\n\n".join(file_sections)
        )
        result = self._backend.generate(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            schema=None,
            sampler=self._sampler,
            deadline=self._limits.llm_timeout_s,
            seed=0,
        )
        data = _parse_json_object(result.text)
        return self._validate_model_payload(data, len(entries))

    def _validate_model_payload(
        self, data: dict[str, Any], file_count: int
    ) -> dict[str, Any]:
        courses = data.get("courses")
        assignments = data.get("assignments")
        if not isinstance(courses, list) or not courses:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "modelo não retornou matérias em courses[]",
                diagnostic=DIAGNOSTIC,
            )
        norm_courses: list[dict[str, Any]] = []
        for entry in courses:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            raw_topics = entry.get("topics")
            topics = (
                [str(t).strip() for t in raw_topics if str(t).strip()]
                if isinstance(raw_topics, list)
                else []
            )
            norm_courses.append({"title": title[:180], "topics": topics[:12]})
        if not norm_courses:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "matérias retornadas sem título válido",
                diagnostic=DIAGNOSTIC,
            )
        norm_assignments: list[dict[str, int]] = []
        if isinstance(assignments, list):
            for entry in assignments:
                if not isinstance(entry, dict):
                    continue
                try:
                    file_idx = int(entry.get("file"))
                    course_idx = int(entry.get("course"))
                except (TypeError, ValueError):
                    continue
                if 1 <= file_idx <= file_count and 1 <= course_idx <= len(
                    norm_courses
                ):
                    norm_assignments.append(
                        {"file": file_idx, "course": course_idx}
                    )
        # Arquivo sem assignment válido → primeira matéria (determinístico).
        assigned = {a["file"] for a in norm_assignments}
        for file_idx in range(1, file_count + 1):
            if file_idx not in assigned:
                norm_assignments.append({"file": file_idx, "course": 1})
        return {"courses": norm_courses, "assignments": norm_assignments}

    # -- API do serviço ----------------------------------------------------

    def suggest(
        self, user_id: str, files: list[tuple[str, bytes]]
    ) -> list[dict[str, Any]]:
        """Analisa os arquivos e cria rascunhos pendentes (um por matéria)."""
        if not files:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "nenhum arquivo enviado para análise",
                diagnostic=DIAGNOSTIC,
            )
        if len(files) > self._limits.max_files:
            raise EduAgentError(
                ErrorCode.RESOURCE_LIMIT,
                f"máximo de {self._limits.max_files} arquivos por análise",
                details={"max_files": self._limits.max_files},
                diagnostic=DIAGNOSTIC,
            )
        entries: list[dict[str, Any]] = []
        for filename, raw in files:
            sample = self._extract_sample(filename, raw)
            entries.append(
                {"filename": filename, "raw": raw, "sample": sample}
            )
        analysis = self._call_model(entries)

        now = self._clock()
        expires = now + timedelta(hours=self._limits.ttl_hours)
        created: list[dict[str, Any]] = []
        for course_idx, course in enumerate(analysis["courses"], start=1):
            member_files = [
                entries[a["file"] - 1]
                for a in analysis["assignments"]
                if a["course"] == course_idx
            ]
            if not member_files:
                # Matéria sem arquivo atribuído não vira rascunho (ruído de
                # agrupamento do modelo nunca aparece na UI).
                continue
            suggestion_id = str(uuid.uuid4())
            staging = self._staging_dir(user_id, suggestion_id)
            staging.mkdir(parents=True, exist_ok=True)
            files_meta: list[dict[str, Any]] = []
            for entry in member_files:
                target = self._staged_file_path(
                    user_id, suggestion_id, entry["filename"]
                )
                target.write_bytes(entry["raw"])
                files_meta.append(
                    {
                        "filename": entry["filename"],
                        "size_bytes": len(entry["raw"]),
                        "sample_chars": len(entry["sample"]),
                    }
                )
            self._store.execute_write(
                user_id,
                [
                    (
                        "INSERT INTO course_suggestions"
                        "(id, user_id, title, topics_json, files_json, status, "
                        "created_at, expires_at) VALUES (?, ?, ?, ?, ?, "
                        "'pending', ?, ?)",
                        (
                            suggestion_id,
                            user_id,
                            course["title"],
                            json.dumps(course["topics"], ensure_ascii=False),
                            json.dumps(files_meta, ensure_ascii=False),
                            now.isoformat(),
                            expires.isoformat(),
                        ),
                    )
                ],
                bump_domain_revision=False,
            )
            created.append(
                {
                    "id": suggestion_id,
                    "title": course["title"],
                    "topics": course["topics"],
                    "files": files_meta,
                    "status": "pending",
                    "created_at": now.isoformat(),
                    "expires_at": expires.isoformat(),
                }
            )
        return created

    def staged_file_path(
        self, user_id: str, suggestion_id: str, filename: str
    ) -> Path:
        """Caminho confinado de um arquivo em staging (preview na UI)."""
        return resolve_owned_path(
            self._root,
            user_id,
            f"staging/{suggestion_id}/{filename}",
        )

    def _staged_file_path(
        self, user_id: str, suggestion_id: str, filename: str
    ) -> Path:
        return self.staged_file_path(user_id, suggestion_id, filename)

    def list_pending(self, user_id: str) -> list[dict[str, Any]]:
        """Rascunhos pendentes não expirados, mais recentes primeiro."""
        now = self._clock().isoformat()
        rows = self._store.fetch_user_rows(
            "SELECT id, title, topics_json, files_json, created_at, "
            "expires_at FROM course_suggestions "
            "WHERE user_id = ? AND status = 'pending' AND expires_at > ? "
            "ORDER BY created_at DESC",
            (user_id, now),
        )
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        try:
            topics = json.loads(row["topics_json"])
        except (json.JSONDecodeError, TypeError):
            topics = []
        try:
            files = json.loads(row["files_json"])
        except (json.JSONDecodeError, TypeError):
            files = []
        return {
            "id": str(row["id"]),
            "title": str(row["title"]),
            "topics": topics if isinstance(topics, list) else [],
            "files": files if isinstance(files, list) else [],
            "status": "pending",
            "created_at": str(row["created_at"]),
            "expires_at": str(row["expires_at"]),
        }

    def get_pending(self, user_id: str, suggestion_id: str) -> dict[str, Any]:
        """Rascunho pendente por ID; expirado/inexistente → SOURCE_UNRESOLVED."""
        row = self._store.fetch_user_rows(
            "SELECT id, title, topics_json, files_json, status, created_at, "
            "expires_at FROM course_suggestions WHERE user_id = ? AND id = ?",
            (user_id, suggestion_id),
        )
        if not row or str(row[0]["status"]) != "pending":
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "sugestão não encontrada ou já resolvida",
                diagnostic=DIAGNOSTIC,
            )
        data = self._row_to_dict(row[0])
        if data["expires_at"] <= self._clock().isoformat():
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "sugestão expirou — reenvie os arquivos no popup +Nova",
                diagnostic=DIAGNOSTIC,
            )
        return data

    def confirm(
        self,
        user_id: str,
        suggestion_id: str,
        *,
        title: str,
        topics: list[str],
        ingest_fn: _INGEST_FN,
    ) -> dict[str, Any]:
        """Aprova o rascunho: cria a matéria real e ingere os arquivos em
        staging pelo caminho normal do Curador (``ingest_fn``)."""
        suggestion = self.get_pending(user_id, suggestion_id)
        staged: list[dict[str, Any]] = []
        for meta in suggestion["files"]:
            path = self._staged_file_path(user_id, suggestion_id, str(meta["filename"]))
            if not path.exists():
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"arquivo em staging ausente: {meta['filename']}",
                    diagnostic=DIAGNOSTIC,
                )
            staged.append({"filename": str(meta["filename"]), "path": path})

        course_id = str(uuid.uuid4())
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                "INSERT INTO courses(id, user_id, title, aliases_json, revision) "
                "VALUES (?, ?, ?, '[]', 1)",
                (course_id, user_id, title),
            )
        ]
        created_topics: list[dict[str, Any]] = []
        for topic_title in topics:
            t_id = str(uuid.uuid4())
            statements.append(
                (
                    "INSERT INTO topics(id, course_id, title, aliases_json, "
                    "revision) VALUES (?, ?, ?, '[]', 1)",
                    (t_id, course_id, topic_title),
                )
            )
            created_topics.append(
                {"id": t_id, "course_id": course_id, "title": topic_title}
            )
        statements.append(
            (
                "UPDATE course_suggestions SET status = 'approved' "
                "WHERE id = ? AND user_id = ?",
                (suggestion_id, user_id),
            )
        )
        self._store.execute_write(
            user_id, statements, bump_domain_revision=True
        )

        # Move os bytes do staging para originals/ e ingere (caminho normal).
        originals_dir = resolve_owned_path(self._root, user_id, "originals")
        originals_dir.mkdir(parents=True, exist_ok=True)
        ingest_results: list[dict[str, Any]] = []
        for entry in staged:
            raw = entry["path"].read_bytes()
            target = resolve_owned_path(
                self._root, user_id, f"originals/{entry['filename']}"
            )
            target.write_bytes(raw)
            result = ingest_fn(user_id, entry["filename"], raw, course_id)
            ingest_results.append({"filename": entry["filename"], **result})
        shutil.rmtree(self._staging_dir(user_id, suggestion_id), ignore_errors=True)
        return {
            "course": {
                "id": course_id,
                "user_id": user_id,
                "title": title,
                "topics": created_topics,
            },
            "ingested": ingest_results,
        }

    def reject(self, user_id: str, suggestion_id: str) -> None:
        """Descarta o rascunho e remove o staging (sem apagar aprovados)."""
        self.get_pending(user_id, suggestion_id)
        self._store.execute_write(
            user_id,
            [
                (
                    "UPDATE course_suggestions SET status = 'rejected' "
                    "WHERE id = ? AND user_id = ?",
                    (suggestion_id, user_id),
                )
            ],
            bump_domain_revision=False,
        )
        shutil.rmtree(self._staging_dir(user_id, suggestion_id), ignore_errors=True)


__all__ = [
    "CourseSuggestionService",
    "SuggestLimits",
]
