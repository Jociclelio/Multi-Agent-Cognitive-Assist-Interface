"""Sugestão de matérias a partir de arquivos soltos na UI (fluxo "+Nova").

Fluxo em duas fases (decisão registrada em 21/11/2026):

- **Fase 1 — classificação por arquivo** (``classify_staged``): cada arquivo
  solto é guardado em staging (``<user>/staging/<batch_id>/<arquivo>``) e
  classificado pelo ``DocumentClassifierService`` (uma chamada ao modelo do
  runtime; resultado cacheado por sha256 em ``doc_classifications``).
- **Fase 2 — agregação** (``aggregate_batch``): uma chamada ao modelo recebe o
  dossiê de TODOS os arquivos do batch (classe + hints de disciplina + tópicos
  vistos + amostra/headings) e decide quantas matérias criar, o título
  (``CÓDIGO — Nome oficial`` quando houver código) e os tópicos — com o
  programa/ementa como fonte canônica e proibição de tópicos genéricos.
- Cada matéria proposta vira rascunho ``pending`` (migração 0008) listado no
  rail como "esperando aprovação"; confirmar cria a matéria e ingere os
  arquivos de staging pelo caminho normal do Curador, ou descarta.

Fail-closed: sem backend admitido, a Fase 1 recusa com ``MODEL_NOT_ADMITTED``
e a UI cai para a aba manual. Staging expira (sweep por mtime, TTL de ensaio).

Todos os valores numéricos são DEFAULTS DE ENSAIO a calibrar — não resultados
medidos (mapa §3).
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.policy import resolve_owned_path

DIAGNOSTIC = "eduagent/services/course_suggest.py"

#: TTL do rascunho pendente (ensaio): após expirar, confirmar recusa 410.
TTL_HOURS = 24

#: TTL de limpeza do staging por mtime (ensaio).
STAGING_TTL_HOURS = 48

#: Teto de arquivos por batch (ensaio).
MAX_FILES_PER_BATCH = 10

CLASS_LABELS = {
    "programa": "📋 Programa",
    "cronograma": "🗓️ Cronograma",
    "lista_exercicios": "📝 Lista de exercícios",
    "material_didatico": "📚 Material didático",
    "outro": "📄 Outro",
}


def _parse_json_object(text: str) -> dict[str, Any]:
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
            ErrorCode.SCHEMA_INVALID, "resposta do modelo não é um objeto"
        )
    return data


@dataclass(frozen=True)
class SuggestLimits:
    """Limites de ensaio da sugestão (mapa §3: defaults a calibrar)."""

    llm_timeout_s: float = 300.0
    ttl_hours: int = TTL_HOURS
    max_files: int = MAX_FILES_PER_BATCH

    @classmethod
    def from_mapping(cls, config: dict[str, Any] | None) -> "SuggestLimits":
        section = (config or {}).get("course_suggest") or {}
        if not isinstance(section, dict):
            section = {}
        return cls(
            llm_timeout_s=float(section.get("timeout_s", 300.0)),
            ttl_hours=int(section.get("ttl_hours", TTL_HOURS)),
            max_files=int(section.get("max_files", MAX_FILES_PER_BATCH)),
        )


class CourseSuggestionService:
    """Rascunhos de matérias propostas (``course_suggestions``, migração 0008)."""

    def __init__(
        self,
        store: Any,
        data_root: Path | str,
        *,
        classifier: Any | None = None,
        backend: Any | None = None,
        limits: SuggestLimits | None = None,
        clock: Callable[[], datetime] | None = None,
        sampler: Any | None = None,
    ) -> None:
        self._store = store
        self._root = Path(data_root)
        self._classifier = classifier
        self._backend = backend
        self._limits = limits or SuggestLimits()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sampler = sampler

    # -- staging -------------------------------------------------------------

    def _staging_root(self, user_id: str) -> Path:
        return resolve_owned_path(self._root, user_id, "staging")

    def _batch_dir(self, user_id: str, batch_id: str) -> Path:
        return resolve_owned_path(self._root, user_id, f"staging/{batch_id}")

    def staged_file_path(
        self, user_id: str, suggestion_id: str, filename: str
    ) -> Path:
        """Caminho confinado de um arquivo em staging (preview na UI).

        Com arquivos por batch, o path real vem do ``staged_rel`` em
        ``files_json``; ``suggestion_id`` é mantido na assinatura para
        compatibilidade (o batch é resolvido pelo registro da sugestão).
        """
        suggestion = self.get_pending(user_id, suggestion_id)
        for meta in suggestion["files"]:
            if str(meta.get("filename")) == filename:
                rel = str(meta.get("staged_rel") or "")
                if rel:
                    return resolve_owned_path(self._root, user_id, rel)
        raise EduAgentError(
            ErrorCode.SOURCE_UNRESOLVED,
            f"arquivo não pertence a esta sugestão: {filename}",
            diagnostic=DIAGNOSTIC,
        )

    def _sweep_staging(self, user_id: str) -> None:
        """Remove batches de staging mais velhos que o TTL (limpeza barata)."""
        root = self._staging_root(user_id)
        if not root.exists():
            return
        cutoff = time.time() - STAGING_TTL_HOURS * 3600
        for child in root.iterdir():
            try:
                if child.is_dir() and child.stat().st_mtime < cutoff:
                    shutil.rmtree(child, ignore_errors=True)
            except OSError:
                continue

    # -- Fase 1: classifica e stageda um arquivo --------------------------------

    def classify_staged(
        self, user_id: str, filename: str, raw: bytes, batch_id: str | None
    ) -> dict[str, Any]:
        """Guarda o arquivo em staging e classifica (Fase 1).

        Retorna o dossiê do arquivo (classe, hints, tópicos vistos) + o
        ``batch_id`` (criado na primeira chamada e reutilizado nas demais).
        """
        if not raw:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID, "arquivo vazio", diagnostic=DIAGNOSTIC
            )
        if self._classifier is None:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "classificador indisponível nesta instalação",
                diagnostic=DIAGNOSTIC,
            )
        self._sweep_staging(user_id)
        batch = batch_id or str(uuid.uuid4())
        batch_dir = self._batch_dir(user_id, batch)
        existing = [p.name for p in batch_dir.iterdir()] if batch_dir.exists() else []
        if filename not in existing and len(existing) >= self._limits.max_files:
            raise EduAgentError(
                ErrorCode.RESOURCE_LIMIT,
                f"máximo de {self._limits.max_files} arquivos por análise",
                details={"max_files": self._limits.max_files},
                diagnostic=DIAGNOSTIC,
            )
        batch_dir.mkdir(parents=True, exist_ok=True)
        target = resolve_owned_path(
            self._root, user_id, f"staging/{batch}/{filename}"
        )
        target.write_bytes(raw)
        meta = self._classifier.classify_bytes(filename, raw)
        return {
            "batch_id": batch,
            "file": {
                "filename": filename,
                "size_bytes": len(raw),
                "sha256": meta["sha256"],
                "doc_class": meta["doc_class"],
                "class_label": CLASS_LABELS.get(meta["doc_class"], "📄 Outro"),
                "confidence": meta["confidence"],
                "disciplina_hints": meta["disciplina_hints"],
                "topics_seen": meta["topics_seen"],
            },
        }

    # -- Fase 2: agrega o batch em propostas --------------------------------------

    def aggregate_batch(self, user_id: str, batch_id: str) -> list[dict[str, Any]]:
        """Lê o staging do batch + classificações e cria rascunhos pendentes."""
        if self._backend is None:
            raise EduAgentError(
                ErrorCode.MODEL_NOT_ADMITTED,
                "agregação exige modelo admitido (mapa §3.1); use a aba manual",
                diagnostic=DIAGNOSTIC,
            )
        batch_dir = self._batch_dir(user_id, batch_id)
        if not batch_dir.exists() or not any(batch_dir.iterdir()):
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "batch de staging não encontrado — reenvie os arquivos",
                diagnostic=DIAGNOSTIC,
            )
        entries: list[dict[str, Any]] = []
        for path in sorted(batch_dir.iterdir()):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            meta = self._classifier.classify_bytes(path.name, raw)
            entries.append(
                {
                    "filename": path.name,
                    "raw": raw,
                    "staged_rel": f"staging/{batch_id}/{path.name}",
                    "doc_class": meta["doc_class"],
                    "disciplina_hints": meta["disciplina_hints"],
                    "topics_seen": meta["topics_seen"],
                    "pages_scanned": meta["pages_scanned"],
                }
            )
        if not entries:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "batch vazio", diagnostic=DIAGNOSTIC
            )
        if len(entries) > self._limits.max_files:
            raise EduAgentError(
                ErrorCode.RESOURCE_LIMIT,
                f"máximo de {self._limits.max_files} arquivos por análise",
                diagnostic=DIAGNOSTIC,
            )
        analysis = self._aggregate(entries)

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
            # Tópicos vazios do modelo → backfill com topics_seen dos arquivos
            # (programa primeiro — fonte canônica; depois material didático).
            if not course["topics"]:
                by_prio = sorted(
                    member_files,
                    key=lambda e: (
                        0 if e["doc_class"] == "programa"
                        else 1 if e["doc_class"] == "material_didatico"
                        else 2
                    ),
                )
                seen: list[str] = []
                for e in by_prio:
                    for t in e["topics_seen"]:
                        if t not in seen:
                            seen.append(t)
                course["topics"] = seen[:10]
            suggestion_id = str(uuid.uuid4())
            files_meta = [
                {
                    "filename": e["filename"],
                    "size_bytes": len(e["raw"]),
                    "doc_class": e["doc_class"],
                    "class_label": CLASS_LABELS.get(e["doc_class"], "📄 Outro"),
                    "staged_rel": e["staged_rel"],
                }
                for e in member_files
            ]
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

    # -- modelo (Fase 2) ------------------------------------------------------

    def _aggregate(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        dossiers: list[str] = []
        for idx, e in enumerate(entries, start=1):
            hints = ", ".join(e["disciplina_hints"]) or "(nenhum)"
            topics = "; ".join(e["topics_seen"]) or "(nenhum)"
            dossiers.append(
                f"[ARQUIVO {idx}] {e['filename']}\n"
                f"  classe: {e['doc_class']}\n"
                f"  disciplina vista: {hints}\n"
                f"  tópicos vistos: {topics}"
            )
        prompt = (
            "Você cria a(s) matéria(s) (disciplinas) a partir do dossiê de "
            "materiais já classificados.\n\n"
            "Dossiê dos arquivos:\n" + "\n\n".join(dossiers) + "\n\n"
            "Responda com UM ÚNICO objeto JSON (sem cercas de código), no "
            "formato exato:\n"
            '{"courses": [{"title": "<nome da matéria>", "topics": '
            '["<tópico>", ...]}], "assignments": [{"file": <índice do arquivo, '
            'int>, "course": <índice da matéria, int>}]}\n\n'
            "Regras:\n"
            "- Agrupe arquivos da MESMA matéria juntos; crie quantas matérias "
            "forem detectadas (pode ser uma só).\n"
            "- TÍTULO: use o nome oficial da disciplina; se houver código "
            "(ex.: MC8322), use o formato 'CÓDIGO — Nome'. NUNCA 'Disciplina "
            "<código>' nem '(2026)' sozinho.\n"
            "- TÓPICOS: o arquivo classe 'programa' (ementa) é a fonte "
            "canônica — use os temas do conteúdo programático. Headings de "
            "material_didático complementam. lista_exercicios não cria tópico "
            "novo. PROIBIDO 'Conteúdo do Capítulo N' sem o assunto real.\n"
            "- 3 a 10 tópicos por matéria, em português, com o nome próprio do "
            "assunto."
        )
        result = self._backend.generate(
            messages=[{"role": "user", "content": prompt}],
            schema=None,
            sampler=self._sampler or self._default_sampler(),
            deadline=self._limits.llm_timeout_s,
            seed=0,
        )
        data = _parse_json_object(result.text)
        return self._validate_model_payload(data, len(entries))

    def _default_sampler(self) -> Any:
        from eduagent.services.model_adapter import Sampler

        # Perfil de agregação (ensaio): baixa temperatura — saída estrutural.
        return Sampler(
            temperature=0.2,
            top_p=0.9,
            top_k=20,
            min_p=0.0,
            presence_penalty=0.0,
            repeat_penalty=1.0,
            thinking=False,
        )

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

    # -- listagem / revisão / confirm / reject ------------------------------------

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
    ) -> dict[str, Any]:
        """Aprova o rascunho: cria a matéria real e move os arquivos de
        staging para ``originals/``. A ingestão NÃO roda aqui — o popup fecha
        na hora e a UI dispara arquivo a arquivo via
        ``POST /library/ingest-original`` (progresso visível no Acervo), como
        no fluxo de upload da Biblioteca."""
        suggestion = self.get_pending(user_id, suggestion_id)
        staged: list[dict[str, Any]] = []
        for meta in suggestion["files"]:
            rel = str(meta.get("staged_rel") or "")
            if not rel:
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"arquivo sem caminho de staging: {meta.get('filename')}",
                    diagnostic=DIAGNOSTIC,
                )
            path = resolve_owned_path(self._root, user_id, rel)
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

        # Move os bytes do staging para originals/ (a ingestão vem depois,
        # arquivo a arquivo, pelo caminho normal do Curador).
        originals_dir = resolve_owned_path(self._root, user_id, "originals")
        originals_dir.mkdir(parents=True, exist_ok=True)
        moved: list[str] = []
        for entry in staged:
            raw = entry["path"].read_bytes()
            target = resolve_owned_path(
                self._root, user_id, f"originals/{entry['filename']}"
            )
            target.write_bytes(raw)
            entry["path"].unlink(missing_ok=True)
            moved.append(entry["filename"])
        self._rmdir_if_empty(self._staging_root(user_id))
        return {
            "course": {
                "id": course_id,
                "user_id": user_id,
                "title": title,
                "topics": created_topics,
            },
            "files": moved,
        }

    def reject(self, user_id: str, suggestion_id: str) -> None:
        """Descarta o rascunho e remove seus arquivos de staging."""
        suggestion = self.get_pending(user_id, suggestion_id)
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
        root = self._staging_root(user_id)
        for meta in suggestion["files"]:
            rel = str(meta.get("staged_rel") or "")
            if rel:
                try:
                    resolve_owned_path(self._root, user_id, rel).unlink(
                        missing_ok=True
                    )
                except EduAgentError:
                    continue
        self._rmdir_if_empty(root)

    def _rmdir_if_empty(self, root: Path) -> None:
        """Remove diretórios de staging vazios (batch pode servir várias
        sugestões — só some quando o último arquivo sai)."""
        try:
            for child in root.iterdir():
                if child.is_dir() and not any(child.iterdir()):
                    child.rmdir()
            while root != root.parent:
                if any(root.iterdir()):
                    return
                root.rmdir()
                root = root.parent
        except OSError:
            return


__all__ = [
    "CourseSuggestionService",
    "SuggestLimits",
    "CLASS_LABELS",
]
