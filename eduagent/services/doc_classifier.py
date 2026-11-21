"""Classificador rápido de documentos (Fase 1 do +Nova e do acervo).

Uma chamada ao **modelo do runtime configurado** por arquivo, com o início do
texto extraído, devolvendo classe da taxonomia fechada
(programa/cronograma/lista_exercicios/material_didatico/outro), confiança,
códigos/nomes de disciplina vistos e tópicos vistos. NÃO é a ingestão — é uma
classificação rápida para alimentar a agregação (Fase 2) e etiquetar o acervo.

- Resultados são guardados em ``doc_classifications`` **por sha256 do
  conteúdo** (migração 0010): mesmo conteúdo nunca é classificado duas vezes.
- Escalada única: se o modelo pedir ``needs_more`` (amostra rasa — capa/sumário
  sem corpo), uma segunda amostra maior (mais páginas, com todos os headings)
  é extraída e a classificação roda de novo. Máximo de 2 chamadas por arquivo.
- Falha do modelo/extrator é propagada como erro tipado no fluxo +Nova; no
  gancho pós-ingestão o chamador decide tolerar (best-effort).

Todos os valores numéricos são DEFAULTS DE ENSAIO a calibrar — não resultados
medidos (mapa §3).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.services.model_adapter import Sampler

DIAGNOSTIC = "eduagent/services/doc_classifier.py"

#: Amostra da 1ª passada: páginas / teto de caracteres (ensaio).
SAMPLE_PAGES_PASS1 = 6
SAMPLE_CHARS_PASS1 = 2000

#: Amostra da escalada (needs_more): mais páginas, priorizando headings.
SAMPLE_PAGES_PASS2 = 30
SAMPLE_CHARS_PASS2 = 6000

DOC_CLASSES = (
    "programa",
    "cronograma",
    "lista_exercicios",
    "material_didatico",
    "outro",
)

_PROMPT_RULES = """Definições:
- programa = ementa/plano de ensino da disciplina (conteúdo programático, avaliação, bibliografia).
- cronograma = calendário de aulas/entregas por data.
- lista_exercicios = lista de exercícios/problemas.
- material_didatico = livro/notas de aula/slides com conteúdo de estudo.
- outro = não se encaixa em nenhuma das anteriores.
Responda APENAS com um objeto JSON (sem cercas de código), no formato exato:
{"doc_class": "<classe>", "confidence": "alta|media|baixa", "needs_more": true|false,
 "disciplina_hints": ["códigos ou nomes de disciplina vistos no texto"],
 "topics_seen": ["temas reais vistos no texto, com nome próprio do assunto"]}
needs_more=true SOMENTE se a amostra não basta para classificar (ex.: só capa
ou sumário, sem corpo). Em topics_seen NUNCA escreva itens genéricos como
"Conteúdo do Capítulo 6" — escreva o assunto do capítulo quando ele aparecer.
topics_seen é OBRIGATÓRIO e não pode ser vazio quando houver qualquer texto ou
imagem legível: liste os temas vistos (em programa, o conteúdo programático
inteiro)."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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
class ClassifierLimits:
    """Limites de ensaio do classificador (mapa §3: defaults a calibrar)."""

    pages_pass1: int = SAMPLE_PAGES_PASS1
    chars_pass1: int = SAMPLE_CHARS_PASS1
    pages_pass2: int = SAMPLE_PAGES_PASS2
    chars_pass2: int = SAMPLE_CHARS_PASS2
    llm_timeout_s: float = 180.0

    @classmethod
    def from_mapping(cls, config: dict[str, Any] | None) -> "ClassifierLimits":
        section = (config or {}).get("doc_classify") or {}
        if not isinstance(section, dict):
            section = {}
        return cls(
            pages_pass1=int(section.get("pages_pass1", SAMPLE_PAGES_PASS1)),
            chars_pass1=int(section.get("chars_pass1", SAMPLE_CHARS_PASS1)),
            pages_pass2=int(section.get("pages_pass2", SAMPLE_PAGES_PASS2)),
            chars_pass2=int(section.get("chars_pass2", SAMPLE_CHARS_PASS2)),
            llm_timeout_s=float(section.get("timeout_s", 180.0)),
        )


class DocumentClassifierService:
    """Classificação rápida por sha256 (tabela ``doc_classifications``)."""

    def __init__(
        self,
        store: Any,
        data_root: Path | str,
        *,
        extractor: Any | None = None,
        backend: Any | None = None,
        limits: ClassifierLimits | None = None,
        clock: Callable[[], datetime] | None = None,
        sampler: Sampler | None = None,
    ) -> None:
        self._store = store
        self._root = Path(data_root)
        self._extractor = extractor
        self._backend = backend
        self._limits = limits or ClassifierLimits()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sampler = sampler

    # -- amostragem --------------------------------------------------------

    def _sample_text(self, raw: bytes, mime: str, *, pages: int, chars: int) -> str:
        """Headings primeiro (são os candidatos naturais a tópico) + corpo."""
        if self._extractor is None or not raw:
            return ""
        try:
            extracted = self._extractor.extract(raw, mime, max_pages=pages)
        except EduAgentError:
            return ""
        headings: list[str] = []
        body: list[str] = []
        budget = chars
        for page in extracted.pages:
            for block in page.blocks:
                text = (block.text or "").strip()
                if not text:
                    continue
                if block.kind == "heading":
                    headings.append(text)
                else:
                    body.append(text)
        parts = []
        if headings:
            parts.append("TÍTULOS DE SEÇÃO VISTOS:\n" + "\n".join(f"- {h}" for h in headings[:60]))
        for text in body:
            if budget <= 0:
                break
            parts.append(text[:budget])
            budget -= len(text)
        return "\n".join(parts)[:chars]

    def _render_page_images(self, raw: bytes, max_images: int) -> list[str]:
        """Renderiza as primeiras páginas do PDF como JPEG base64 (fallback de
        visão para PDFs image-based que o Docling não consegue ler)."""
        if not raw or not raw.startswith(b"%PDF"):
            return []
        try:
            import base64 as _b64
            import io

            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(io.BytesIO(raw))
            images: list[str] = []
            for i in range(min(max_images, len(pdf))):
                page = pdf[i]
                bitmap = page.render(scale=1.6)
                pil = bitmap.to_pil()
                buf = io.BytesIO()
                pil.convert("RGB").save(buf, format="JPEG", quality=72)
                images.append(_b64.b64encode(buf.getvalue()).decode("ascii"))
                page.close()
            pdf.close()
            return images
        except Exception:  # noqa: BLE001 — render é best-effort
            return []

    # -- modelo --------------------------------------------------------------

    def _call_model(
        self, filename: str, sample: str, images: list[str] | None = None
    ) -> dict[str, Any]:
        if self._backend is None:
            raise EduAgentError(
                ErrorCode.MODEL_NOT_ADMITTED,
                "classificação exige modelo admitido (mapa §3.1)",
                diagnostic=DIAGNOSTIC,
            )
        vision_note = ""
        if images:
            vision_note = (
                "\n\nAs PRIMEIRAS PÁGINAS do documento estão anexadas como "
                "imagem — leia o texto DELAS (título, ementa, sumário) para "
                "classificar e extrair nome da disciplina e tópicos."
            )
        prompt = (
            "Você classifica um material de estudo a partir do nome do arquivo "
            "e de uma amostra do conteúdo.\n\n"
            f"ARQUIVO: {filename}\n\nAMOSTRA DO CONTEÚDO:\n"
            f"{sample or '(sem texto extraído)'}\n"
            + vision_note + "\n\n"
            + _PROMPT_RULES
        )
        if images:
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            for b64 in images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    }
                )
            messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
        else:
            messages = [{"role": "user", "content": prompt}]
        result = self._backend.generate(
            messages=messages,
            schema=None,
            sampler=self._sampler or self._default_sampler(),
            deadline=self._limits.llm_timeout_s,
            seed=0,
        )
        return self._validate(_parse_json_object(result.text))

    def _default_sampler(self) -> Any:
        from eduagent.services.model_adapter import Sampler

        # Perfil de classificação (ensaio): baixa temperatura para consistência
        # — diferente do sampler da tutoria (criativo por natureza).
        return Sampler(
            temperature=0.2,
            top_p=0.9,
            top_k=20,
            min_p=0.0,
            presence_penalty=0.0,
            repeat_penalty=1.0,
            thinking=False,
        )

    def _validate(self, data: dict[str, Any]) -> dict[str, Any]:
        doc_class = str(data.get("doc_class") or "").strip().lower()
        if doc_class not in DOC_CLASSES:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"doc_class inválida do modelo: {doc_class!r}",
                diagnostic=DIAGNOSTIC,
            )
        confidence = str(data.get("confidence") or "baixa").strip().lower()
        if confidence not in ("alta", "media", "baixa"):
            confidence = "baixa"
        needs_more = bool(data.get("needs_more"))
        # Aliases: modelos desviam do nome exato da chave com frequência.
        hints = data.get("disciplina_hints", data.get("hints"))
        topics = data.get("topics_seen", data.get("topics"))
        return {
            "doc_class": doc_class,
            "confidence": confidence,
            "needs_more": needs_more,
            "disciplina_hints": (
                [str(h).strip()[:120] for h in hints if str(h).strip()][:8]
                if isinstance(hints, list)
                else []
            ),
            "topics_seen": (
                [str(t).strip()[:120] for t in topics if str(t).strip()][:15]
                if isinstance(topics, list)
                else []
            ),
        }

    # -- persistência ----------------------------------------------------------

    def get_by_sha256(self, sha256: str) -> dict[str, Any] | None:
        rows = self._store.fetch_user_rows(
            "SELECT sha256, doc_class, confidence, disciplina_hints_json, "
            "topics_json, pages_scanned, classified_at FROM doc_classifications "
            "WHERE sha256 = ?",
            (sha256,),
        )
        if not rows:
            return None
        r = rows[0]
        try:
            hints = json.loads(r["disciplina_hints_json"])
        except (json.JSONDecodeError, TypeError):
            hints = []
        try:
            topics = json.loads(r["topics_json"])
        except (json.JSONDecodeError, TypeError):
            topics = []
        return {
            "sha256": str(r["sha256"]),
            "doc_class": str(r["doc_class"]),
            "confidence": str(r["confidence"]),
            "disciplina_hints": hints if isinstance(hints, list) else [],
            "topics_seen": topics if isinstance(topics, list) else [],
            "pages_scanned": int(r["pages_scanned"]),
            "classified_at": str(r["classified_at"]),
        }

    def _save(self, meta: dict[str, Any]) -> None:
        self._store.execute_system_write(
            [
                (
                    "INSERT INTO doc_classifications(sha256, doc_class, "
                    "confidence, disciplina_hints_json, topics_json, "
                    "pages_scanned, classified_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(sha256) DO NOTHING",
                    (
                        meta["sha256"],
                        meta["doc_class"],
                        meta["confidence"],
                        json.dumps(meta["disciplina_hints"], ensure_ascii=False),
                        json.dumps(meta["topics_seen"], ensure_ascii=False),
                        meta["pages_scanned"],
                        self._clock().isoformat(),
                    ),
                )
            ],
        )

    # -- API pública -------------------------------------------------------------

    def classify_bytes(
        self, filename: str, raw: bytes, mime: str | None = None
    ) -> dict[str, Any]:
        """Classifica o conteúdo (reusa por sha256; escalada única)."""
        if mime is None:
            import mimetypes

            mime, _ = mimetypes.guess_type(filename)
            mime = mime or "application/octet-stream"
        digest = sha256_bytes(raw)
        cached = self.get_by_sha256(digest)
        if cached is not None:
            return cached
        if self._backend is None:
            raise EduAgentError(
                ErrorCode.MODEL_NOT_ADMITTED,
                "classificação exige modelo admitido (mapa §3.1)",
                diagnostic=DIAGNOSTIC,
            )
        sample = self._sample_text(
            raw, mime, pages=self._limits.pages_pass1, chars=self._limits.chars_pass1
        )
        # Fallback de visão: PDF sem texto extraível (slides image-based) →
        # manda as primeiras páginas como imagem ao modelo de visão.
        images: list[str] = []
        if len(sample) < 200:
            images = self._render_page_images(raw, max_images=4)
        result = self._call_model(filename, sample, images)
        pages_scanned = self._limits.pages_pass1
        needs_more = result.pop("needs_more", False)
        if needs_more:
            sample2 = self._sample_text(
                raw,
                mime,
                pages=self._limits.pages_pass2,
                chars=self._limits.chars_pass2,
            )
            images2 = self._render_page_images(raw, max_images=8) if len(sample2) < 200 else []
            result = self._call_model(filename, sample2, images2)
            result.pop("needs_more", None)
            pages_scanned = self._limits.pages_pass2
        meta = {
            "sha256": digest,
            "doc_class": result["doc_class"],
            "confidence": result["confidence"],
            "disciplina_hints": result["disciplina_hints"],
            "topics_seen": result["topics_seen"],
            "pages_scanned": pages_scanned,
        }
        self._save(meta)
        return meta

    def classify_bytes_if_needed(self, filename: str, raw: bytes) -> dict[str, Any] | None:
        """Best-effort para o gancho pós-ingestão: None se não classificou."""
        try:
            return self.classify_bytes(filename, raw)
        except EduAgentError:
            return None


__all__ = [
    "DocumentClassifierService",
    "ClassifierLimits",
    "DOC_CLASSES",
    "sha256_bytes",
]
