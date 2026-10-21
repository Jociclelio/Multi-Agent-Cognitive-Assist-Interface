"""Montador de contexto com checagem de síntese (mapa normativo §7; task 010).

Contratos implementados:

- **Orçamento contado após template/serialização (§7)**: a contagem de
  tokens é feita sobre o texto **renderizado** (contador injetável — a
  contagem exata do Bonsai é calibração de validação, §3) e o total obedece
  ``input + 16384 + 2048 + 1024 ≤ 32768`` — entrada máxima **13.312
  tokens**. Os quatro componentes da fórmula são constantes normativas do
  §7/§3.
- **Ordem de montagem (§7)**: instrução e schema → skill → tarefa/item/
  rubrica → âncoras/fatos confirmados → fontes → memória → turnos recentes.
  A serialização preserva exatamente essa ordem.
- **Redução (§7)**: sob pressão de orçamento, primeiro reduzem-se **fontes
  periféricas** (rank menor primeiro), depois **segmenta-se** (corte em
  fronteira de token); só depois se resume — e o resumo é **síntese
  verificada**: nasce dos originais, com verificação exata de datas,
  números, polaridade, ajuda e estado (``verify_claim_against_sources`` —
  números por igualdade numérica sem substring, datas por valor
  normalizado, polaridade/estado com falha fechado ante negação/inversão
  na fonte). Falha de verificação **mantém os originais** ou pede divisão
  (``RESOURCE_LIMIT``) — nunca substitui por síntese não verificada, nunca
  remove a **rubrica necessária** e continua avaliando (se instrução/item/
  rubrica/fatos obrigatórios não cabem, o erro é tipado antes de qualquer
  avaliação).
- **Eventos nunca são apagados por compactação**: o montador é somente
  leitura; a síntese publicada é artefato derivado (responsabilidade da
  publicação em ``services/memory.py``).

Nenhum número aqui é resultado medido: a fórmula do orçamento é
especificação do §7; os limiares de redução derivam dela.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable, Protocol, Sequence

from eduagent.contracts import EduAgentError, ErrorCode

_DIAGNOSTIC = "eduagent/context.py"

# ---------------------------------------------------------------------------
# Orçamento do §7 (normativo): input + 16384 + 2048 + 1024 ≤ 32768
# ---------------------------------------------------------------------------

WINDOW_TOKENS = 32768
MAX_OUTPUT_TOKENS = 16384
TOOL_RESERVE_TOKENS = 2048
MARGIN_TOKENS = 1024
#: Entrada máxima (§7): 32768 − 16384 − 2048 − 1024 = 13312 tokens.
INPUT_BUDGET_TOKENS = (
    WINDOW_TOKENS - MAX_OUTPUT_TOKENS - TOOL_RESERVE_TOKENS - MARGIN_TOKENS
)


class ContextSection(str, Enum):
    """Seções na ordem de montagem do §7."""

    INSTRUCTION_SCHEMA = "instruction_schema"
    SKILL = "skill"
    TASK_ITEM_RUBRIC = "task_item_rubric"
    ANCHORS_FACTS = "anchors_facts"
    SOURCES = "sources"
    MEMORY = "memory"
    RECENT_TURNS = "recent_turns"


#: Ordem normativa do §7 — a serialização segue exatamente esta sequência.
SECTION_ORDER: tuple[ContextSection, ...] = (
    ContextSection.INSTRUCTION_SCHEMA,
    ContextSection.SKILL,
    ContextSection.TASK_ITEM_RUBRIC,
    ContextSection.ANCHORS_FACTS,
    ContextSection.SOURCES,
    ContextSection.MEMORY,
    ContextSection.RECENT_TURNS,
)


class TokenCounter(Protocol):
    """Contador de tokens injetável (mesma fronteira da 007)."""

    def count(self, text: str) -> int: ...


@dataclass(frozen=True)
class SourceItem:
    """Fonte com rank (rank 1 = mais relevante; ranks maiores são fontes
    periféricas — as primeiras a sair na redução, §7)."""

    source_id: str
    text: str
    rank: int


@dataclass(frozen=True)
class ContextInput:
    """Entradas por seção. Campos ``None``/listas vazias produzem seção
    ausente (a seção não é serializada); seções obrigatórias presentes não
    são removíveis na redução."""

    instruction: str | None = None
    schema: str | None = None
    skill: str | None = None
    task: str | None = None
    rubric: str | None = None
    anchor_facts: tuple[str, ...] = ()
    sources: tuple[SourceItem, ...] = ()
    memory_lines: tuple[str, ...] = ()
    recent_turns: tuple[str, ...] = ()  # em ordem; o último é o mais recente


@dataclass(frozen=True)
class ContextAssembly:
    """Contexto montado: texto serializado, contagens pós-serialização e
    ações de redução registradas (observabilidade local, §12)."""

    text: str
    input_tokens: int
    section_tokens: dict[ContextSection, int]
    actions: tuple[str, ...] = ()
    budget: int = INPUT_BUDGET_TOKENS

    @property
    def total_tokens(self) -> int:
        """Tokens totais do texto final serializado (contagem única, pós-
        serialização — §7)."""
        return self._total

    _total: int = 0

    @property
    def within_budget(self) -> bool:
        return self._total <= self.budget


#: Assinatura do sintetizador injetável: recebe os textos dos originais e
#: devolve (texto_da_síntese, claims). A verificação é feita aqui.
Summarizer = Callable[[Sequence[str]], tuple[str, Sequence[str]]]

#: Verificador de claim: exatidão de datas/números/polaridade/ajuda/estado.
ClaimVerifier = Callable[[str, Sequence[str]], bool]


class ContextBuilder:
    """Montagem de contexto na ordem do §7 com orçamento pós-serialização e
    redução (fontes periféricas → segmentar → sintetizar, verificada)."""

    def __init__(
        self,
        token_counter: TokenCounter,
        *,
        summarizer: Summarizer | None = None,
        claim_verifier: ClaimVerifier | None = None,
    ) -> None:
        self._counter = token_counter
        self._summarizer = summarizer
        self._claim_verifier: ClaimVerifier = (
            claim_verifier or verify_claim_against_sources
        )

    # -- templates (serialização) ---------------------------------------------

    def _render(self, section: ContextSection, data: ContextInput) -> str | None:
        if section is ContextSection.INSTRUCTION_SCHEMA:
            if data.instruction is None and data.schema is None:
                return None
            parts = []
            if data.instruction is not None:
                parts.append(f"INSTRUÇÃO:\n{data.instruction}")
            if data.schema is not None:
                parts.append(f"SCHEMA:\n{data.schema}")
            return "\n\n".join(parts)
        if section is ContextSection.SKILL:
            return f"SKILL:\n{data.skill}" if data.skill else None
        if section is ContextSection.TASK_ITEM_RUBRIC:
            if data.task is None and data.rubric is None:
                return None
            parts = []
            if data.task is not None:
                parts.append(f"TAREFA/ITEM:\n{data.task}")
            if data.rubric is not None:
                parts.append(f"RUBRICA:\n{data.rubric}")
            return "\n\n".join(parts)
        if section is ContextSection.ANCHORS_FACTS:
            if not data.anchor_facts:
                return None
            lines = "\n".join(f"- {fact}" for fact in data.anchor_facts)
            return f"ÂNCORAS/FATOS CONFIRMADOS:\n{lines}"
        if section is ContextSection.SOURCES:
            if not data.sources:
                return None
            lines = "\n".join(
                f"[{source.rank}] {source.text}"
                for source in sorted(data.sources, key=lambda s: s.rank)
            )
            return f"FONTES:\n{lines}"
        if section is ContextSection.MEMORY:
            if not data.memory_lines:
                return None
            lines = "\n".join(f"- {line}" for line in data.memory_lines)
            return f"MEMÓRIA:\n{lines}"
        if section is ContextSection.RECENT_TURNS:
            if not data.recent_turns:
                return None
            lines = "\n".join(
                f"turno {i}: {turn}" for i, turn in enumerate(data.recent_turns, 1)
            )
            return f"TURNOS RECENTES:\n{lines}"
        raise EduAgentError(  # pragma: no cover — enum fechado
            ErrorCode.INTERNAL_FAILURE,
            f"seção desconhecida: {section}",
            diagnostic=_DIAGNOSTIC,
        )

    # -- custo pós-serialização (§7: contagem após template) ------------------

    def _context_cost(self, input_text: str, data: ContextInput) -> int:
        """Custo total do contexto serializado: entrada + seções
        renderizadas, cada uma contada **após** o template (§7).

        As ações de redução NÃO entram no texto serializado (são metadados
        de observabilidade em ``ContextAssembly.actions``) — incluí-las no
        custo criaria retroalimentação: cada redução registrada consumiria
        orçamento e exigiria novas reduções."""
        parts = [
            rendered
            for section in SECTION_ORDER
            if (rendered := self._render(section, data)) is not None
        ]
        return self._counter.count(input_text + "\n\n" + "\n\n".join(parts))

    # -- montagem -------------------------------------------------------------

    def assemble(self, input_text: str, data: ContextInput) -> ContextAssembly:
        """Monta o contexto: contagem **após** template/serialização (§7),
        ordem do mapa, redução de fontes periféricas → segmentação → síntese
        verificada → memória → turnos antigos; rubrica jamais removida.

        Excedente insolúvel → ``RESOURCE_LIMIT`` (pede divisão; §12: nunca
        saída parcial silenciosamente aprovada).
        """
        input_tokens = self._counter.count(input_text)
        if input_tokens > INPUT_BUDGET_TOKENS:
            raise EduAgentError(
                ErrorCode.RESOURCE_LIMIT,
                f"entrada de {input_tokens} tokens excede a entrada máxima "
                f"{INPUT_BUDGET_TOKENS} (mapa §7) — divida a entrada",
                diagnostic=_DIAGNOSTIC,
            )
        actions: list[str] = []
        data = self._fit(input_text, data, actions)
        section_tokens: dict[ContextSection, int] = {}
        parts: list[str] = []
        for section in SECTION_ORDER:
            rendered = self._render(section, data)
            if rendered is None:
                continue
            section_tokens[section] = self._counter.count(rendered)
            parts.append(rendered)
        final_text = input_text + "\n\n" + "\n\n".join(parts)
        total = self._counter.count(final_text)
        if total > INPUT_BUDGET_TOKENS:  # pragma: no cover — _fit garante
            raise EduAgentError(
                ErrorCode.RESOURCE_LIMIT,
                f"contexto com {total} tokens excede a entrada máxima "
                f"{INPUT_BUDGET_TOKENS} após redução (mapa §7) — pede "
                "divisão; rubrica/fatos obrigatórios não são removidos",
                diagnostic=_DIAGNOSTIC,
            )
        return ContextAssembly(
            text=final_text,
            input_tokens=input_tokens,
            section_tokens=section_tokens,
            actions=tuple(actions),
            _total=total,
        )

    # -- redução (§7: fontes periféricas → segmentar → resumir) ---------------

    def _fit(
        self, input_text: str, data: ContextInput, actions: list[str]
    ) -> ContextInput:
        """Reduz o conteúdo até caber no orçamento de entrada, na ordem do
        §7: fontes periféricas → segmentação → síntese verificada → itens de
        memória → turnos antigos. Rubrica/instrução/fatos obrigatórios nunca
        são removidos — excedente neles é ``RESOURCE_LIMIT`` (pede divisão).
        """
        budget = INPUT_BUDGET_TOKENS
        if self._context_cost(input_text, data) <= budget:
            return data

        # 1. Seções obrigatórias: instrução/schema, skill, tarefa/item/
        #    rubrica, âncoras/fatos confirmados e o turno mais recente (a
        #    rubrica JAMAIS é removida — §7: "jamais remover rubrica
        #    necessária e continuar avaliando"; o turno mais recente é
        #    reservado para a continuidade do diálogo).
        turn_reserve = (
            (data.recent_turns[-1],) if data.recent_turns else ()
        )
        required_only = replace(
            data,
            sources=(),
            memory_lines=(),
            recent_turns=turn_reserve,
        )
        required_cost = self._context_cost(input_text, required_only)
        if required_cost > budget:
            raise EduAgentError(
                ErrorCode.RESOURCE_LIMIT,
                "seções obrigatórias (instrução/skill/item/rubrica/fatos "
                f"confirmados/turno recente) excedem o orçamento de entrada "
                f"({required_cost} > {budget}; mapa §7) — divisão "
                "obrigatória; a rubrica não é removida para continuar "
                "avaliando",
                diagnostic=_DIAGNOSTIC,
            )

        # 2. Fontes: reduz periféricas (rank alto) → segmenta → sintetiza.
        #    O orçamento das fontes já desconta o turno reservado (etapa 1).
        sources = self._fit_sources(
            data.sources, input_text, required_only, budget, actions
        )
        data = replace(data, sources=sources)
        if self._context_cost(input_text, data) <= budget:
            return data

        # 3. Memória: corta pela cauda (itens menos relevantes por último na
        #    lista de entrada) — fatos obrigatórios estão em ÂNCORAS/FATOS e
        #    não são afetados.
        memory_lines = list(data.memory_lines)
        while memory_lines:
            memory_lines.pop()
            data = replace(data, memory_lines=tuple(memory_lines))
            actions.append("memória reduzida por orçamento")
            if self._context_cost(input_text, data) <= budget:
                return data

        # 4. Turnos recentes: remove os mais antigos primeiro; o turno mais
        #    recente é mantido (§7: "turnos recentes").
        turns = list(data.recent_turns)
        while len(turns) > 1:
            turns.pop(0)
            data = replace(data, recent_turns=tuple(turns))
            actions.append("turnos antigos reduzidos")
            if self._context_cost(input_text, data) <= budget:
                return data
        raise EduAgentError(
            ErrorCode.RESOURCE_LIMIT,
            "nem o turno mais recente cabe no orçamento após todas as "
            "reduções do §7 (fontes → segmentação → síntese verificada → "
            "memória → turnos antigos) — divida a entrada",
            diagnostic=_DIAGNOSTIC,
        )

    def _fits_with_sources(
        self,
        input_text: str,
        base_data: ContextInput,
        sources: Sequence[SourceItem],
        budget: int,
    ) -> bool:
        return (
            self._context_cost(
                input_text, replace(base_data, sources=tuple(sources))
            )
            <= budget
        )

    def _fit_sources(
        self,
        sources: tuple[SourceItem, ...],
        input_text: str,
        base_data: ContextInput,
        budget: int,
        actions: list[str],
    ) -> tuple[SourceItem, ...]:
        """Redução de fontes na ordem do §7: (a) remove fontes periféricas
        (rank maior primeiro); (b) segmenta a fonte que não couber inteira
        (corte em fronteira de token, marcado); (c) só então resume — com
        **síntese verificada**; verificação falhada mantém originais ou pede
        divisão (RESOURCE_LIMIT). Nunca remove a rubrica nem fatos
        obrigatórios (fora deste escopo)."""
        if not sources:
            return sources
        ordered = sorted(sources, key=lambda s: s.rank)
        kept: list[SourceItem] = []

        for item in ordered:
            if self._fits_with_sources(
                input_text, base_data, [*kept, item], budget
            ):
                kept.append(item)
            else:
                # Fonte não coube: tenta as seguintes (uma fonte posterior
                # menor ainda pode caber); a de fora vai para segmentação/
                # síntese/divisão.
                continue
        dropped = len(ordered) - len(kept)
        if dropped:
            actions.append(f"fontes periféricas reduzidas={dropped}")

        # (b) segmentação: se há fonte fora e sobrou espaço, tenta o primeiro
        #     segmento que couber (corte em fronteira de token). O resto é
        #     calculado EXPLICITAMENTE, sem pressuposto de prefixo: o laço
        #     guloso pode pular uma fonte grande e aceitar uma menor
        #     posterior — fonte já mantida não reaparece no resto
        #     (revisão da 010).
        kept_ids = {id(item) for item in kept}
        rest = [item for item in ordered if id(item) not in kept_ids]
        if rest:
            segment = self._segment(
                rest[0], input_text, base_data, tuple(kept), budget
            )
            if segment is not None:
                kept.append(segment)
                rest = rest[1:]
                actions.append("fonte segmentada")
        if not rest:
            return tuple(kept)

        # (c) síntese verificada dos originais restantes (§7): falha mantém
        # os originais que couberem ou pede divisão — nunca resumo não
        # verificado, nunca remoção da rubrica.
        synthesized = self._try_summarize(
            [item.text for item in rest],
            input_text,
            base_data,
            tuple(kept),
            budget,
            actions,
        )
        if synthesized is not None:
            kept.append(synthesized)
            return tuple(kept)
        # Falha de síntese (ou indisponível): **mantém os originais
        # selecionados** (§7) que couberem e registra as fontes fora do
        # orçamento — divisão só é exigida quando nenhuma original cabe.
        if kept:
            actions.append(
                "síntese verificada indisponível — originais mantidos, "
                f"{len(rest)} fonte(s) fora do orçamento"
            )
            return tuple(kept)
        # Sem nenhum original no orçamento e sem síntese possível: pede
        # divisão (nunca contexto vazio silencioso, §12).
        raise EduAgentError(
            ErrorCode.RESOURCE_LIMIT,
            "fontes excedem o orçamento e a síntese verificada não está "
            "disponível ou falhou (mapa §7: reduzir/segmentar antes de "
            "resumir; falha mantém originais) — divida a consulta",
            diagnostic=_DIAGNOSTIC,
        )

    def _segment(
        self,
        item: SourceItem,
        input_text: str,
        base_data: ContextInput,
        kept: tuple[SourceItem, ...],
        budget: int,
        actions: Sequence[str] = (),
    ) -> SourceItem | None:
        """Primeiro segmento que couber no orçamento (corte em fronteira de
        token sobre o texto original, marcado com ``[…]``)."""
        words = item.text.split()
        best: str | None = None
        low, high = 0, len(words)
        while low <= high:
            mid = (low + high) // 2
            candidate = " ".join(words[:mid]) if mid else ""
            if not candidate:
                high = mid - 1
                continue
            candidate_item = SourceItem(
                source_id=item.source_id, text=candidate + " […]", rank=item.rank
            )
            if self._fits_with_sources(
                input_text, base_data, [*kept, candidate_item], budget
            ):
                best = candidate + " […]"
                low = mid + 1
            else:
                high = mid - 1
        if best is None:
            return None
        return SourceItem(source_id=item.source_id, text=best, rank=item.rank)

    def _try_summarize(
        self,
        texts: list[str],
        input_text: str,
        base_data: ContextInput,
        kept: tuple[SourceItem, ...],
        budget: int,
        actions: list[str],
    ) -> SourceItem | None:
        """Síntese verificada (§7): nasce dos originais; cada claim é
        conferido exatamente (datas, números, polaridade, ajuda, estado)
        contra os originais; falha mantém os originais (retorna ``None`` →
        chamador pede divisão). Não encadeia resumo de resumo: claims de
        sínteses anteriores não são originais válidos — o verificador exige
        suporte literal nos originais fornecidos."""
        if self._summarizer is None:
            return None
        summary_text, claims = self._summarizer(texts)
        for claim in claims:
            if not self._claim_verifier(claim, texts):
                actions.append("síntese falhou na verificação — originais mantidos")
                return None
        synthesis = SourceItem(
            source_id="synthesis",
            text=f"[resumo verificado] {summary_text}",
            rank=0,
        )
        if not self._fits_with_sources(
            input_text, base_data, [*kept, synthesis], budget
        ):
            actions.append("síntese não coube — originais mantidos")
            return None
        actions.append("síntese verificada publicada no contexto")
        return synthesis


# ---------------------------------------------------------------------------
# Verificação exata de claims (§7: datas, números, polaridade, ajuda, estado)
# ---------------------------------------------------------------------------

_DATE_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DATE_BR_RE = re.compile(r"\d{2}/\d{2}/\d{4}")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_HELP_RE = re.compile(r"ajuda n[íi]vel\s+(\d+)")

#: Polaridade e estado: tokens canônicos (valores dos enums do contrato
#: Assessment/TopicState) — a checagem é exata contra os originais.
POLARITY_TOKENS = ("correct", "incorrect", "partial", "undecidable")
STATE_TOKENS = ("insufficient", "mixed", "favorable")


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _number_value(token: str) -> float:
    return float(token.replace(",", "."))


def _has_number(sources: str, token: str) -> bool:
    """Igualdade numérica exata (§7) contra os tokens extraídos por
    ``_NUMBER_RE`` dos originais — **sem** pré-checagem por substring:
    ``"12"`` não verifica ``"120"``; ``"7"`` verifica ``"7,0"`` (mesmo
    valor numérico). Número genuinamente presente continua verificando."""
    try:
        value = _number_value(token)
    except ValueError:
        return False
    for match in _NUMBER_RE.finditer(sources):
        try:
            if _number_value(match.group()) == value:
                return True
        except ValueError:  # pragma: no cover — regex só gera números
            continue
    return False


def _date_tokens(text: str) -> set[str]:
    """Datas de ``text`` normalizadas para ISO (``dd/mm/aaaa`` →
    ``aaaa-mm-dd``): a conferência é pelo **valor** da data, não por
    substring — a mesma data em formatos distintos verifica; datas
    distintas não (§7: checar exatamente datas)."""
    tokens = {match.group() for match in _DATE_ISO_RE.finditer(text)}
    for match in _DATE_BR_RE.finditer(text):
        day, month, year = match.group().split("/")
        tokens.add(f"{year}-{month}-{day}")
    return tokens


#: Opostos canônicos de polaridade: fonte que traz o oposto do token do
#: claim contradiz o claim — presença literal do token não prova claims
#: opostos (revisão da 010; falha fechada, §12).
_POLARITY_OPPOSITES = {"correct": "incorrect", "incorrect": "correct"}

#: Marcadores de negação: ocorrência do token precedida por negação na fonte
#: contradiz o claim — checagem conservadora (falha fechada mantendo os
#: originais).
_NEGATION_WORDS = frozenset(
    {"não", "nao", "not", "nunca", "never", "sem", "without"}
)
_NEGATION_WINDOW_WORDS = 2
_NEGATION_WINDOW_CHARS = 32

_WORD_RE = re.compile(r"[a-záâãàéêíóôõúüç]+")


def _negated_before(sources: str, start: int) -> bool:
    """True se a ocorrência que começa em ``start`` é precedida, dentro da
    janela de palavras, por marcador de negação — a fonte nega o token e não
    o suporta (falha fechada)."""
    window = sources[max(0, start - _NEGATION_WINDOW_CHARS) : start]
    words = _WORD_RE.findall(window)
    return any(
        word in _NEGATION_WORDS
        for word in words[-_NEGATION_WINDOW_WORDS :]
    )


def _token_supported(sources: str, token: str) -> bool:
    """Suporte do token de polaridade/estado na fonte (§7/§12): presença
    literal **não basta** — a fonte que traz o token oposto ou o traz sob
    negação contradiz o claim; falha fechada preserva os originais."""
    if not re.search(rf"\b{token}\b", sources):
        return False
    opposite = _POLARITY_OPPOSITES.get(token)
    if opposite and re.search(rf"\b{opposite}\b", sources):
        return False
    return not any(
        _negated_before(sources, match.start())
        for match in re.finditer(rf"\b{token}\b", sources)
    )


def verify_claim_against_sources(
    claim: str, source_texts: Sequence[str]
) -> bool:
    """Verificação exata de UM claim contra os originais (§7): toda data,
    número, polaridade, nível de ajuda e estado presente no claim deve ter
    suporte exato nos originais — números por igualdade numérica contra os
    tokens extraídos (sem substring: ``"12"`` não verifica ``"120"``), datas
    por valor normalizado, polaridade/ajuda/estado sem contradição (fonte
    que traz o oposto ou nega o token falha fechado). Claim sem **nenhum**
    elemento verificável é não verificável → falha (mantém originais; nunca
    aprovar parcial silenciosamente, §12)."""
    normalized_claim = _norm(claim)
    sources = "\n".join(_norm(text) for text in source_texts)
    checked = False

    claim_dates = _date_tokens(normalized_claim)
    source_dates = _date_tokens(sources)
    for date in sorted(claim_dates):
        checked = True
        if date not in source_dates:
            return False

    numbers = _NUMBER_RE.findall(normalized_claim)
    for token in numbers:
        # Datas já foram conferidas; um número extra no claim precisa de
        # suporte nos originais (exatidão de números, §7).
        checked = True
        if not _has_number(sources, token):
            return False

    for token in POLARITY_TOKENS:
        if re.search(rf"\b{token}\b", normalized_claim):
            checked = True
            if not _token_supported(sources, token):
                return False

    for token in STATE_TOKENS:
        if re.search(rf"\b{token}\b", normalized_claim):
            checked = True
            if not _token_supported(sources, token):
                return False

    for match in _HELP_RE.finditer(normalized_claim):
        checked = True
        if not _has_number(sources, match.group(1)):
            return False
        # Negação da ajuda na fonte também contradiz o claim (falha
        # fechada): "não houve ajuda nível 2" não suporta "ajuda nível 2".
        claim_level = _number_value(match.group(1))
        for source_match in _HELP_RE.finditer(sources):
            if _number_value(source_match.group(1)) == claim_level and (
                _negated_before(sources, source_match.start())
            ):
                return False

    return checked


__all__ = [
    "ContextAssembly",
    "ContextBuilder",
    "ContextInput",
    "ContextSection",
    "INPUT_BUDGET_TOKENS",
    "MARGIN_TOKENS",
    "MAX_OUTPUT_TOKENS",
    "POLARITY_TOKENS",
    "SECTION_ORDER",
    "STATE_TOKENS",
    "SourceItem",
    "TOOL_RESERVE_TOKENS",
    "WINDOW_TOKENS",
    "verify_claim_against_sources",
]
