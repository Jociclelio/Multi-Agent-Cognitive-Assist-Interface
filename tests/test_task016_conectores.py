"""Testes de aceite da task 016 — conectores opcionais: curadoria web e sync
de calendário (mapa §6 curadoria web, §9 sync, §10 tabela ``web.search/fetch``
e ``calendar.apply``, §13.9).

Não é a suíte quantitativa da etapa 8 (mapa de testes): testes locais de
curta duração, sem rede real e sem credenciais — o transporte HTTP dos
conectores é injetado (a barreira de IP privado/loopback fica FORA do
transporte, em ``policy.assert_public_url``/``assert_redirect_target``, e é
exercitada com resolução real de nomes literais/localhost).

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| W1 | sem conector de busca configurado, ``search`` recusa CONNECTOR_DISABLED (§6) |
| W2 | rota curate com rede habilitada e sem conector → CONNECTOR_DISABLED no network_gate (§6/§10) |
| W3 | rota curate com conector de fetch (busca desabilitada) → CONNECTOR_DISABLED no web_search (§6) |
| W4 | fetch: estados text_read/metadata_only/unavailable com URL final, data/hash e fonte; vídeo sem transcrição só metadados, nunca resumido |
| W5 | redirects: dois hops com revalidação OK; terceiro recusado; redirect para IP privado negado por código (§6/§10) |
| W6 | fetch bloqueia loopback/privado com resolução real; rota curate revalida destino de candidato (herdado da 014, retestado) |
| W7 | limites: corpo 5 MiB+1 recusado; timeout → unavailable; até 5 candidatos na rota mesmo com payload maior (§6) |
| W8 | cache offline marcado com data original e fonte cache, nunca como consulta atual (§6) |
| S1 | CalDAV create: PUT href estável com If-None-Match: *; 201 APPLIED; 412 CONFLICT (§9) |
| S2 | CalDAV update: PUT href do read com If-Match ETag; 204 APPLIED; 412 CONFLICT; 404 NOT_APPLIED (§9) |
| S3 | CalDAV delete: DELETE href com If-Match; 204 APPLIED; 404 APPLIED (mapeamento local documentado); 412 CONFLICT (§9) |
| S4 | CalDAV read_all/read_one: multistatus com uid/etag/ics; ausente → None (§9) |
| S5 | timeout no PUT → ConnectorTimeout → reconcile por leitura, sem retry cego; leitura também inacessível → UNKNOWN_EFFECT (§9/§11) |
| S6 | end-to-end apply_plan com CalDAV: cria eventos; alteração externa (412) → CONFLICT e novo preview exigido (§9) |
| S7 | fábrica: sem config/credenciais → None → apply reporta CONNECTOR_DISABLED mantendo ICS/preview (§9) |
| S8 | adaptador MCP: allowlist de read/create/update/delete com IDs/precondições; fora da lista negado por código (§9/§10) |
| S9 | admissão individual: registro caldav ADMITIDO, google NÃO ADMITIDO com motivo; construção Google recusada (§9) |
| D1 | dívida da 014a: TIMEOUT pós-consume_llm e pré-enqueue reembolsa o débito (§12) |
| W9 | transporte real (``urllib_transport``) impõe o §6: leitura limitada a ``MAX_BODY_BYTES + 1`` (incluindo caminho ``HTTPError``) e timeout de 10 s — provado contra servidor HTTP local real chamando o transporte diretamente, fora da barreira de IP privado da rota (correção 016a) |
| W10 | rota curate corta ``max_results`` com ``min(max_results, _MAX_CANDIDATES)`` antes de chamar ``search`` (correção 016a) |
| S10 | redirect malicioso do CalDAV: transporte real sem auto-follow; destino de origem distinta recusado com ``ConnectorError`` sem contatar o segundo host e sem reenviar a credencial Basic — provado com servidores HTTP locais reais (correção 016a) |
| S11 | endurecimento do parse: multistatus com DTD/entidades recusado, bytes pré-parse limitados (1 MiB, default de ensaio) e teto de corpo no REPORT (5 MiB, default de ensaio — §9 não prescreve valor) (correção 016a) |
| S12 | wiring: ``RuntimeContext`` constrói ``calendar_connector=build_calendar_connector(...)`` — config CalDAV presente chega ao grafo; ausente mantém ``CONNECTOR_DISABLED`` com ICS/preview (correção 016a) |
"""

from __future__ import annotations

import http.server
import threading
import time
import uuid as _uuid
from collections.abc import Mapping
from datetime import date, datetime, time as _dt_time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eduagent.contracts import (
    EduAgentError,
    ErrorCode,
    ScheduleProposal,
)
from eduagent.graph import EduAgentGraph
from eduagent.policy import GenerationGate, TurnLimits
from eduagent.runtime import RuntimeContext
from eduagent.services.calendar import (
    CalendarService,
    SyncOutcome,
)
from eduagent.services.effects import EffectsService
from eduagent.services.sync_connectors import (
    CONNECTOR_ADMISSION,
    CaldavConfig,
    CaldavConnector,
    ConnectorError,
    GoogleCalendarConnector,
    MAX_MULTISTATUS_BYTES,
    MAX_REPORT_BODY_BYTES,
    McpCalendarAdapter,
    build_calendar_connector,
    connector_admission,
    make_urllib_transport,
    parse_multistatus,
)
from eduagent.services.web import (
    DEFAULT_TIMEOUT_S,
    MAX_BODY_BYTES,
    MAX_CANDIDATES,
    ResourceState,
    WebFetchConnector,
    urllib_transport,
)
from eduagent.storage.checkpoints import SQLiteCheckpointer
from eduagent.storage.repository import DomainStore

UTC = timezone.utc

UID = "123e4567-e89b-12d3-a456-426614174000"
SESSION = "00000000-0000-0000-0000-000000000163"
T0 = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
D0 = date(2026, 10, 21)
BASE_URL = "https://cal.exemplo.local/user/calendario/"


def _uid(n: int) -> _uuid.UUID:
    return _uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


def _utc(day: date, minute: int) -> datetime:
    return datetime.combine(day, _dt_time(0, 0), tzinfo=UTC) + timedelta(
        minutes=minute
    )


def _transport_ok(
    url: str,
    *,
    content_type: str = "text/html; charset=utf-8",
    body: bytes = b"<html>conteudo</html>",
):
    def transport(requested: str, timeout: float):
        assert requested == url
        assert timeout > 0
        return 200, {"Content-Type": content_type}, body

    return transport


# ---------------------------------------------------------------------------
# W — curadoria web (mapa §6)
# ---------------------------------------------------------------------------


class TestCuradoriaWeb:
    def test_w1_search_sem_conector_connectora_desabilitado(self):
        connector = WebFetchConnector()
        with pytest.raises(EduAgentError) as exc:
            connector.search("circuitos", language="pt", max_results=3)
        assert exc.value.code is ErrorCode.RESOURCE_LIMIT
        assert "CONNECTOR_DISABLED" in exc.value.message

    def test_w2_rota_curate_sem_conector_connectora_desabilitado(self, tmp_path):
        env = open_curate_stack(tmp_path, config={"network_enabled": True})
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca",
                intent="curate",
                payload={"query": "dedup"},
            )
            assert result.status == "failed"
            error = result.state.errors[0]
            assert error.code is ErrorCode.RESOURCE_LIMIT
            assert "CONNECTOR_DISABLED" in error.message
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_w3_rota_curate_com_fetch_sem_busca_connectora_desabilitado(
        self, tmp_path
    ):
        env = open_curate_stack(
            tmp_path,
            web_connector=WebFetchConnector(),
            config={"network_enabled": True},
        )
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca",
                intent="curate",
                payload={"query": "dedup"},
            )
            assert result.status == "failed"
            error = result.state.errors[0]
            assert error.code is ErrorCode.RESOURCE_LIMIT
            assert "CONNECTOR_DISABLED" in error.message
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_w4_fetch_estados_url_data_hash_e_fonte(self):
        connector = WebFetchConnector(
            transport=_transport_ok(
                "https://exemplo.valido.org/artigo", body=b"<html>texto</html>"
            ),
            clock=lambda: T0,
        )
        resource = connector.fetch("https://exemplo.valido.org/artigo")
        assert resource["state"] == "text_read"
        assert resource["url"] == "https://exemplo.valido.org/artigo"
        assert resource["captured_at"] == T0.isoformat()
        assert resource["source"] == "network"
        assert len(resource["hash"]) == 64
        assert resource["cached"] is False
        # Vídeo sem transcrição: só metadados — nunca lido como texto (§6).
        video = WebFetchConnector(
            transport=_transport_ok(
                "https://exemplo.valido.org/aula.mp4",
                content_type="video/mp4",
                body=b"\x00\x01video",
            ),
            clock=lambda: T0,
        ).fetch("https://exemplo.valido.org/aula.mp4")
        assert video["state"] == ResourceState.METADATA_ONLY.value
        assert video["text"] is None
        # Resposta 404: unavailable com razão explícita.
        def transport_404(requested: str, timeout: float):
            return 404, {"Content-Type": "text/plain"}, b""

        miss = WebFetchConnector(
            transport=transport_404, clock=lambda: T0
        ).fetch("https://exemplo.valido.org/ausente")
        assert miss["state"] == "unavailable"
        assert "404" in miss["reason"]
        assert miss["hash"] is None
        assert miss["captured_at"] == T0.isoformat()

    def test_w4b_claims_do_grafo_marcam_video_como_metadados(self, tmp_path):
        connector = _FakeWebConnectorVideo()
        env = open_curate_stack(
            tmp_path,
            web_connector=connector,
            config={"network_enabled": True},
        )
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca",
                intent="curate",
                payload={"query": "aula"},
            )
            assert result.status == "completed"
            claims = result.output["curated_web"]
            video = [c for c in claims if c["access"] == "metadata_only"]
            assert video and "metadados" in video[0]["note"]
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_w5_dois_redirects_com_revalidacao_e_terceiro_recusado(self):
        # Dois redirects: a → b → c (final).
        hops = [
            "https://exemplo.valido.org/a",
            "https://93.184.216.34/b",
            "https://93.184.216.34/c",
        ]
        calls: list[str] = []

        def transport(requested: str, timeout: float):
            calls.append(requested)
            index = hops.index(requested)
            if index < len(hops) - 1:
                return 302, {"Location": hops[index + 1]}, b""
            return 200, {"Content-Type": "text/plain"}, b"fim"

        connector = WebFetchConnector(transport=transport, clock=lambda: T0)
        resource = connector.fetch(hops[0])
        assert resource["state"] == "text_read"
        assert resource["url"] == hops[2]  # dois redirects: URL final é a 3ª
        assert resource["redirect_chain"] == [hops[1], hops[2]]
        assert calls == hops
        # Terceiro redirect excede o limite normativo (§6, default de ensaio).
        chained = WebFetchConnector(
            transport=_chain_transport(hops), max_redirects=2
        ).fetch(hops[0])
        assert chained["state"] == "unavailable"
        assert "redirects" in chained["reason"]

    def test_w5b_redirect_para_ip_privado_negado_por_codigo(self):
        def transport(requested: str, timeout: float):
            return 302, {"Location": "http://10.0.0.1/segredo"}, b""

        connector = WebFetchConnector(transport=transport)
        with pytest.raises(EduAgentError) as exc:
            connector.fetch("https://exemplo.valido.org/redireciona")
        assert exc.value.code is ErrorCode.TOOL_DENIED
        assert "não público" in exc.value.message

    def test_w6_fetch_bloqueia_loopback_e_privado_resolucao_real(self):
        called = []

        def transport(requested: str, timeout: float):  # nunca deve ser chamado
            called.append(requested)
            return 200, {}, b"x"

        connector = WebFetchConnector(transport=transport)
        for url in (
            "http://127.0.0.1/segredo",
            "http://localhost/segredo",
            "http://192.168.0.1/segredo",
            "http://[::1]/segredo",
            "ftp://exemplo.valido.org/arquivo",
        ):
            with pytest.raises(EduAgentError) as exc:
                connector.fetch(url)
            assert exc.value.code is ErrorCode.TOOL_DENIED, url
        assert called == []

    def test_w6b_rota_curate_revalida_destino_do_candidato(self, tmp_path):
        env = open_curate_stack(
            tmp_path,
            web_connector=_FakeWebConnectorPrivado(),
            config={"network_enabled": True},
        )
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca",
                intent="curate",
                payload={"query": "dedup"},
            )
            assert result.status == "failed"
            error = result.state.errors[0]
            assert error.code is ErrorCode.TOOL_DENIED
            assert "não público" in error.message
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_w7_corpo_acima_de_5mib_e_timeout_ficam_indisponiveis(self):
        big = WebFetchConnector(
            transport=_transport_ok(
                "https://exemplo.valido.org/grande",
                body=b"x" * (MAX_BODY_BYTES + 1),
            )
        ).fetch("https://exemplo.valido.org/grande")
        assert big["state"] == "unavailable"
        assert "corpo excede" in big["reason"]

        def transport_lento(requested: str, timeout: float):
            raise TimeoutError("estourou o timeout")

        lento = WebFetchConnector(transport=transport_lento).fetch(
            "https://exemplo.valido.org/lento"
        )
        assert lento["state"] == "unavailable"
        assert "TimeoutError" in lento["reason"]

        def transport_instavel(requested: str, timeout: float):
            raise ConnectionError("conexão recusada")

        instavel = WebFetchConnector(transport=transport_instavel).fetch(
            "https://exemplo.valido.org/instavel"
        )
        assert instavel["state"] == "unavailable"
        assert "ConnectionError" in instavel["reason"]

    def test_w7b_limite_de_candidatos_na_rota(self, tmp_path):
        env = open_curate_stack(
            tmp_path,
            web_connector=_FakeWebConnectorMuitosCandidatos(),
            config={"network_enabled": True},
        )
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca",
                intent="curate",
                payload={"query": "aula", "max_results": 50},
            )
            assert result.status == "completed"
            claims = result.output["curated_web"]
            # §6: "até 5 candidatos/3 fetches" — 7 candidatos e payload com
            # max_results=50 não ampliam os limites: a rota busca no máximo
            # 3 recursos e publica só o que foi efetivamente lido.
            assert len(claims) == 3
            assert {c["url"] for c in claims} == {
                "https://exemplo.valido.org/item0",
                "https://exemplo.valido.org/item1",
                "https://exemplo.valido.org/item2",
            }
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_w7c_max_candidates_acima_do_normativo_e_recusado(self):
        with pytest.raises(EduAgentError) as exc:
            WebFetchConnector(max_candidates=MAX_CANDIDATES + 1)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_w8_cache_offline_marcado_com_data_original(self, tmp_path):
        cache_dir = tmp_path / "cache-web"
        clock_now = {"now": T0}
        url = "https://exemplo.valido.org/artigo"

        def advance_minutes(minutes: int) -> datetime:
            return T0 + timedelta(minutes=minutes)

        primeiro = WebFetchConnector(
            transport=_transport_ok(url, body=b"<html>texto</html>"),
            cache_dir=cache_dir,
            clock=lambda: clock_now["now"],
        ).fetch(url)
        assert primeiro["cached"] is False
        assert primeiro["source"] == "network"

        clock_now["now"] = advance_minutes(30)
        # Consulta atual falha; cache entra MARCADO com a data original (§6).
        def transport_fora_do_ar(requested: str, timeout: float):
            raise TimeoutError("fora do ar")

        fallback = WebFetchConnector(
            transport=transport_fora_do_ar,
            cache_dir=cache_dir,
            clock=lambda: clock_now["now"],
        ).fetch(url)
        assert fallback["cached"] is True
        assert fallback["source"] == "cache"
        assert fallback["captured_at"] == T0.isoformat()  # data da captura
        assert fallback["state"] == "text_read"
        assert "cache offline" in fallback["reason"]
        assert fallback["hash"] == primeiro["hash"]
        # Cache vazio não vira conteúdo: falha permanece unavailable.
        sem_cache = WebFetchConnector(
            transport=transport_fora_do_ar,
            cache_dir=tmp_path / "cache-vazio",
        ).fetch("https://exemplo.valido.org/outro")
        assert sem_cache["state"] == "unavailable"
        assert sem_cache["cached"] is False

    def test_w10_rota_corta_max_results_antes_de_chamar_search(
        self, tmp_path
    ):
        """Correção 016a (achado GLM-A2): o payload não faz ``search`` ver
        pedido acima do limite normativo — ``min(max_results, 5)`` ANTES da
        chamada (o corte pós-busca é mantido em segunda camada)."""
        received: list[int] = []

        class _FakeWebConnectorRegistra:
            def search(self, query, language, max_results):
                received.append(int(max_results))
                return [
                    {"url": "https://exemplo.valido.org/item0", "title": "0"}
                ]

            def fetch(self, url):
                return {
                    "url": url,
                    "state": "text_read",
                    "hash": "ab" * 32,
                    "captured_at": T0.isoformat(),
                }

        env = open_curate_stack(
            tmp_path,
            web_connector=_FakeWebConnectorRegistra(),
            config={"network_enabled": True},
        )
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca",
                intent="curate",
                payload={"query": "aula", "max_results": 50},
            )
            assert result.status == "completed"
            assert received == [MAX_CANDIDATES]  # 5, nunca 50 (§6)
            # Sem payload: default normativo preservado.
            result2 = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca 2",
                intent="curate",
                payload={"query": "aula"},
            )
            assert result2.status == "completed"
            assert received == [MAX_CANDIDATES, MAX_CANDIDATES]
        finally:
            env.store.close()
            env.checkpointer.close()


class _HttpServerLocal:
    """Servidor HTTP local REAL em 127.0.0.1 (porta efêmera, sem rede
    externa) para exercitar os transportes reais diretamente — FORA da
    barreira de IP privado/loopback da rota (camadas distintas: o teste
    chama o transporte, não ``fetch``/``read_all`` com destino loopback).
    ``respond(method, path, headers, body) -> (status, extra_headers,
    payload)`` decide a resposta; toda requisição é registrada."""

    def __init__(self, respond) -> None:
        self.requests_seen: list[tuple[str, str, dict[str, str]]] = []
        self._respond = respond
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                outer.requests_seen.append(
                    (self.command, self.path, dict(self.headers))
                )
                status, extra, payload = outer._respond(
                    self.command, self.path, self.headers, body
                )
                self.send_response(status)
                for key, value in (extra or {}).items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload or b"")))
                self.end_headers()
                if payload:
                    self.wfile.write(payload)

            do_GET = _handle
            do_PUT = _handle
            do_POST = _handle
            do_DELETE = _handle
            do_REPORT = _handle

            def log_message(self, *args) -> None:  # silencioso
                pass

        self._server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), Handler
        )
        self.port = int(self._server.server_address[1])
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        self._thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


class TestTransporteRealWeb:
    """W9 (correção 016a, achado LUNA-A1): o limite "10s/5MiB" do §6 vale no
    transporte real — leitura limitada a ``MAX_BODY_BYTES + 1`` (inclusive no
    caminho ``HTTPError``) e timeout imposto — provado contra servidor HTTP
    local real chamando ``urllib_transport`` diretamente (a barreira de IP
    privado da rota é outra camada e não se aplica aqui)."""

    def test_w9_transporte_real_limita_leitura_a_max_body_mais_um(self):
        excesso = 4096
        total = MAX_BODY_BYTES + excesso

        def respond(method, path, headers, body):
            return 200, {"Content-Type": "text/plain"}, b"x" * total

        server = _HttpServerLocal(respond)
        try:
            status, headers, payload = urllib_transport(
                f"{server.url}/grande", DEFAULT_TIMEOUT_S
            )
        finally:
            server.close()
        assert status == 200
        # Discriminante: exatamente MAX+1 bytes lidos — nem um byte a mais
        # do limite normativo é baixado (mutação read() sem limite falha).
        assert len(payload) == MAX_BODY_BYTES + 1
        assert len(payload) > MAX_BODY_BYTES  # excesso é detectável
        # O excesso mapeia ao estado tipado unavailable (mesma forma do W7):
        connector = WebFetchConnector()
        resource = connector._build_resource(
            f"{server.url}/grande",
            {"Content-Type": "text/plain"},
            payload,
            [],
        )
        assert resource["state"] == "unavailable"
        assert "corpo excede" in resource["reason"]

    def test_w9b_transporte_real_limita_leitura_no_caminho_httperror(self):
        excesso = 2048
        total = MAX_BODY_BYTES + excesso

        def respond(method, path, headers, body):
            return 404, {"Content-Type": "text/plain"}, b"y" * total

        server = _HttpServerLocal(respond)
        try:
            status, headers, payload = urllib_transport(
                f"{server.url}/ausente", DEFAULT_TIMEOUT_S
            )
        finally:
            server.close()
        assert status == 404
        # Caminho HTTPError (exc.read) também é limitado a MAX+1.
        assert len(payload) == MAX_BODY_BYTES + 1

    def test_w9c_timeout_imposto_no_transporte_real(self):
        def respond(method, path, headers, body):
            time.sleep(1.5)  # excede o timeout curto do teste
            return 200, {"Content-Type": "text/plain"}, b"tarde"

        server = _HttpServerLocal(respond)
        try:
            with pytest.raises(TimeoutError):
                urllib_transport(f"{server.url}/lento", 0.25)
        finally:
            server.close()

    def test_w9d_timeout_default_do_transporte_real_e_dez_segundos(self):
        import inspect

        signature = inspect.signature(urllib_transport)
        assert signature.parameters["timeout_s"].default is DEFAULT_TIMEOUT_S
        assert DEFAULT_TIMEOUT_S == 10.0  # §6: "10s/5MiB"


class _FakeWebConnectorVideo:
    """Conector duplo (como na 014) com candidato de vídeo para exercitar a
    regra §6 do grafo: vídeo sem transcrição só por metadados."""

    def search(self, query, language, max_results):
        return [{"url": "https://exemplo.valido.org/aula.mp4", "title": "Aula"}]

    def fetch(self, url):
        return {
            "url": url,
            "state": "metadata_only",
            "hash": "cd" * 32,
            "captured_at": T0.isoformat(),
        }


class _FakeWebConnectorPrivado:
    """Candidato apontando para IP privado — a rota deve revalidar (§10)."""

    def search(self, query, language, max_results):
        return [{"url": "http://10.0.0.1/segredo", "title": "X"}]

    def fetch(self, url):  # pragma: no cover — não deve ser alcançado
        raise AssertionError("fetch não deveria ocorrer com destino privado")


class _FakeWebConnectorMuitosCandidatos:
    """Sete candidatos — a rota deve manter no máximo 5 (§6)."""

    def search(self, query, language, max_results):
        return [
            {"url": f"https://exemplo.valido.org/item{i}", "title": str(i)}
            for i in range(7)
        ]

    def fetch(self, url):
        return {
            "url": url,
            "state": "text_read",
            "hash": "ab" * 32,
            "captured_at": T0.isoformat(),
        }


def _chain_transport(hops: list[str]):
    """Cadeia com um redirect a mais que o limite: o último hop responde
    302 para um destino extra — excede o máximo normativo de redirects."""

    def transport(requested: str, timeout: float):
        index = hops.index(requested)
        if index == len(hops) - 1:
            return 302, {"Location": "https://93.184.216.34/excedente"}, b""
        if index < len(hops) - 1:
            return 302, {"Location": hops[index + 1]}, b""
        return 200, {"Content-Type": "text/plain"}, b"fim"

    return transport


# ---------------------------------------------------------------------------
# S — sync de calendário: CalDAV, MCP, admissão (mapa §9/§10)
# ---------------------------------------------------------------------------


class FakeCaldavServer:
    """Servidor CalDAV falso (transporte injetado, sem rede real): registra
    requisições, aplica precondições condicionais e simula timeout/alteração
    externa. Nenhuma semântica além de RFC 4791 básica é assumida."""

    def __init__(
        self,
        initial: dict[str, dict[str, Any]] | None = None,
        *,
        timeout_after_put: bool = False,
        external_change: bool = False,
    ) -> None:
        # href -> {"etag": str, "ics": str}
        self.events: dict[str, dict[str, Any]] = dict(initial or {})
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.timeout_after_put = timeout_after_put
        self.external_change = external_change
        self._etag_counter = 0

    def transport(
        self, method: str, url: str, body: bytes, headers: Mapping[str, str]
    ) -> tuple[int, dict[str, str], bytes]:
        self.requests.append((method, url, dict(headers)))
        if self.timeout_after_put and any(
            m == "PUT" for m, _, _ in self.requests
        ):
            raise TimeoutError("simulado: sem resposta")
        if method == "REPORT":
            return 207, {}, self._multistatus()
        if method == "PUT":
            if self.external_change:
                return 412, {}, b""
            if_none_match = headers.get("If-None-Match")
            if_match = headers.get("If-Match")
            if if_none_match == "*":
                if url in self.events:
                    return 412, {}, b""
                self._etag_counter += 1
                self.events[url] = {
                    "etag": f"etag-{self._etag_counter}",
                    "ics": body.decode("utf-8"),
                }
                return 201, {}, b""
            if url not in self.events:
                return 404, {}, b""
            if if_match != self.events[url]["etag"]:
                return 412, {}, b""
            self._etag_counter += 1
            self.events[url] = {
                "etag": f"etag-{self._etag_counter}",
                "ics": body.decode("utf-8"),
            }
            return 204, {}, b""
        if method == "DELETE":
            if self.external_change:
                return 412, {}, b""
            if url not in self.events:
                return 404, {}, b""
            if_match = headers.get("If-Match")
            if if_match != self.events[url]["etag"]:
                return 412, {}, b""
            del self.events[url]
            return 204, {}, b""
        raise ConnectorError(f"método inesperado: {method}")

    def _multistatus(self) -> bytes:
        parts = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">',
        ]
        for href, event in self.events.items():
            ics = (
                event["ics"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace("\r\n", "&#13;&#10;")
            )
            parts.append(
                f"<d:response><d:href>{href}</d:href>"
                "<d:propstat><d:prop>"
                f'<d:getetag>"{event["etag"]}"</d:getetag>'
                f"<c:calendar-data>{ics}</c:calendar-data>"
                "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
                "</d:response>"
            )
        parts.append("</d:multistatus>")
        return "".join(parts).encode("utf-8")


def _ics_for(uid: str) -> str:
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//EduAgent-OS//0.1//PT\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        "DTSTAMP:20261020T120000Z\r\n"
        "DTSTART:20261021T090000Z\r\n"
        "DTEND:20261021T100000Z\r\n"
        "SUMMARY:Estudo\r\n"
        "SEQUENCE:0\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


class TestCaldavConnector:
    def test_s1_create_com_if_none_match_star_e_href_estavel(self):
        server = FakeCaldavServer()
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=server.transport
        )
        uid = str(_uid(9001))
        outcome = connector.create(
            "calendar.sync", uid, _ics_for(uid).encode("utf-8")
        )
        assert outcome is SyncOutcome.APPLIED
        method, url, headers = server.requests[0]
        assert method == "PUT"
        assert url == f"{BASE_URL}{uid}.ics"  # href estável por UID (§9)
        assert headers["If-None-Match"] == "*"
        # Criação sobre recurso existente → precondição falhada → CONFLICT.
        outcome2 = connector.create(
            "calendar.sync", uid, _ics_for(uid).encode("utf-8")
        )
        assert outcome2 is SyncOutcome.CONFLICT

    def test_s1b_create_sem_if_none_match_star_recusado(self):
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=FakeCaldavServer().transport
        )
        with pytest.raises(EduAgentError) as exc:
            connector.create(
                "calendar.sync",
                str(_uid(1)),
                _ics_for(str(_uid(1))).encode("utf-8"),
                if_none_match_star=False,
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_s2_update_com_if_match_etag(self):
        uid = str(_uid(9002))
        server = FakeCaldavServer(
            initial={
                f"{BASE_URL}{uid}.ics": {
                    "etag": "etag-1",
                    "ics": _ics_for(uid),
                }
            }
        )
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=server.transport
        )
        remote = connector.read_one("calendar.sync", uid)
        assert remote is not None and remote.etag == "etag-1"
        outcome = connector.update(
            "calendar.sync",
            uid,
            remote.href,
            _ics_for(uid).encode("utf-8"),
            if_match_etag=remote.etag,
        )
        assert outcome is SyncOutcome.APPLIED
        method, url, headers = server.requests[-1]
        assert method == "PUT"
        assert url == remote.href  # href do read reutilizado (estável)
        assert headers["If-Match"] == "etag-1"
        # ETag divergente → alteração externa → CONFLICT.
        outcome2 = connector.update(
            "calendar.sync",
            uid,
            remote.href,
            _ics_for(uid).encode("utf-8"),
            if_match_etag="etag-antigo",
        )
        assert outcome2 is SyncOutcome.CONFLICT
        # Recurso inexistente → NOT_APPLIED.
        outcome3 = connector.update(
            "calendar.sync",
            uid,
            f"{BASE_URL}ausente.ics",
            _ics_for(uid).encode("utf-8"),
            if_match_etag="etag-1",
        )
        assert outcome3 is SyncOutcome.NOT_APPLIED
        # Sem ETag do read anterior não há precondição: escrita incondicional
        # é recusada por código (§9 — update é sempre condicional).
        with pytest.raises(EduAgentError) as exc:
            connector.update(
                "calendar.sync",
                uid,
                remote.href,
                _ics_for(uid).encode("utf-8"),
                if_match_etag=None,
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_s3_delete_com_if_match_e_404_mapeado(self):
        uid = str(_uid(9003))
        server = FakeCaldavServer(
            initial={
                f"{BASE_URL}{uid}.ics": {
                    "etag": "etag-7",
                    "ics": _ics_for(uid),
                }
            }
        )
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=server.transport
        )
        href = f"{BASE_URL}{uid}.ics"
        outcome = connector.delete(
            "calendar.sync", uid, href, if_match_etag="etag-errado"
        )
        assert outcome is SyncOutcome.CONFLICT
        outcome2 = connector.delete(
            "calendar.sync", uid, href, if_match_etag="etag-7"
        )
        assert outcome2 is SyncOutcome.APPLIED
        # Já ausente: estado igual ao desejado — APPLIED (escolha local
        # documentada: evita reenvio de remoção inexistente).
        outcome3 = connector.delete(
            "calendar.sync", uid, href, if_match_etag="etag-7"
        )
        assert outcome3 is SyncOutcome.APPLIED

    def test_s4_read_all_parse_multistatus(self):
        uid = str(_uid(9004))
        server = FakeCaldavServer(
            initial={
                f"{BASE_URL}{uid}.ics": {
                    "etag": "etag-2",
                    "ics": _ics_for(uid),
                }
            }
        )
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=server.transport
        )
        events = connector.read_all("calendar.sync")
        assert len(events) == 1
        assert events[0].uid == uid
        assert events[0].etag == "etag-2"
        assert events[0].event_ics is not None
        assert events[0].href == f"{BASE_URL}{uid}.ics"
        assert connector.read_one("calendar.sync", "outro") is None

    def test_s4b_report_com_status_invalido_levanta_connector_error(self):
        def transport(method, url, body, headers):
            return 500, {}, b"erro"

        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=transport
        )
        with pytest.raises(ConnectorError):
            connector.read_all("calendar.sync")

    def test_s5_timeout_reconcilia_por_leitura_sem_retry_cego(self, tmp_path):
        store, effects, service, confirmation = _confirmed_plan(tmp_path)
        server = FakeCaldavServer(timeout_after_put=True)
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=server.transport
        )
        report = service.apply_plan(
            UID, confirmation.plan_id, connector=connector
        )
        # PUT uma única vez (sem retry cego); leitura também inacessível
        # após o timeout → efeito permanece UNKNOWN_EFFECT (§9/§11).
        puts = [r for r in server.requests if r[0] == "PUT"]
        assert len(puts) == 1
        assert report.status is SyncOutcome.UNKNOWN_EFFECT
        assert "sem retry" in report.detail or "UNKNOWN_EFFECT" in report.detail

    def test_s5b_timeout_com_leitura_ok_reconciliado(self, tmp_path):
        store, effects, service, confirmation = _confirmed_plan(tmp_path)
        server = FakeCaldavServer()
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=server.transport
        )
        # PUT responde timeout (efeito possível), REPORT continua ok.
        original = server.transport

        def transport_com_timeout_put(method, url, body, headers):
            if method == "PUT":
                server.requests.append((method, url, dict(headers)))
                raise TimeoutError("sem resposta")
            return original(method, url, body, headers)

        connector2 = CaldavConnector(
            CaldavConfig(base_url=BASE_URL),
            transport=transport_com_timeout_put,
        )
        report = service.apply_plan(
            UID, confirmation.plan_id, connector=connector2
        )
        assert report.status is SyncOutcome.NOT_APPLIED
        create_results = [
            op for op in report.ops if op.kind.value == "create"
        ]
        assert create_results
        assert all(
            op.outcome is SyncOutcome.NOT_APPLIED for op in create_results
        )
        assert "reconciliado por leitura" in create_results[0].detail

    def test_s6_end_to_end_applied_e_conflito_externo(self, tmp_path):
        store, effects, service, confirmation = _confirmed_plan(tmp_path)
        server = FakeCaldavServer()
        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=server.transport
        )
        report = service.apply_plan(
            UID, confirmation.plan_id, connector=connector
        )
        assert report.status is SyncOutcome.APPLIED
        assert all(op.outcome is SyncOutcome.APPLIED for op in report.ops)
        assert len(server.events) == 1
        # Reaplicar sem mudança: nenhum efeito novo (estado remoto igual).
        report2 = service.apply_plan(
            UID, confirmation.plan_id, connector=connector
        )
        assert report2.status is SyncOutcome.APPLIED
        assert report2.ops == ()
        # Alteração externa: precondição falhada → CONFLICT e novo preview.
        server.external_change = True
        uid = str(_uid(9001))
        desired_ics = server.events[f"{BASE_URL}{uid}.ics"]["ics"].replace(
            "SUMMARY:Estudo", "SUMMARY:Estudo (externo)"
        )
        server.events[f"{BASE_URL}{uid}.ics"]["ics"] = desired_ics
        report3 = service.apply_plan(
            UID, confirmation.plan_id, connector=connector
        )
        assert report3.status is SyncOutcome.CONFLICT
        assert "novo preview" in report3.detail

    def test_s7_fabrica_sem_config_devolve_none_e_apply_connectora(self, tmp_path):
        assert build_calendar_connector(None) is None
        assert build_calendar_connector({}) is None
        assert build_calendar_connector({"calendar_sync_enabled": True}) is None
        connector = build_calendar_connector(
            {
                "calendar_sync_enabled": True,
                "calendar_sync": {"base_url": BASE_URL},
            }
        )
        assert isinstance(connector, CaldavConnector)
        # Sem conector: apply mantém ICS/preview e reporta CONNECTOR_DISABLED.
        store, effects, service, confirmation = _confirmed_plan(tmp_path)
        report = service.apply_plan(UID, confirmation.plan_id, connector=None)
        assert report.status is SyncOutcome.UNCHANGED
        assert "CONNECTOR_DISABLED" in report.detail

    def test_s7b_configuracao_base_url_invalida_recusada(self):
        with pytest.raises(EduAgentError) as exc:
            CaldavConnector(CaldavConfig(base_url="ftp://x/y"))
        assert exc.value.code is ErrorCode.SCHEMA_INVALID


class TestMcpCalendarAdapter:
    def _server(self):
        return FakeCaldavServer()

    def test_s8_allowlist_e_precondicoes(self):
        server = self._server()
        adapter = McpCalendarAdapter(
            CaldavConnector(
                CaldavConfig(base_url=BASE_URL), transport=server.transport
            )
        )
        names = [tool["name"] for tool in adapter.list_tools()]
        assert names == [
            "calendar.read",
            "calendar.create",
            "calendar.update",
            "calendar.delete",
        ]
        uid = str(_uid(9005))
        # Fora da allowlist: negado por código (§10).
        with pytest.raises(EduAgentError) as exc:
            adapter.call_tool("shell.exec", {"cmd": "rm -rf"})
        assert exc.value.code is ErrorCode.TOOL_DENIED
        # create sem if_none_match_star=true: negado (§9).
        with pytest.raises(EduAgentError) as exc:
            adapter.call_tool(
                "calendar.create",
                {
                    "uid": uid,
                    "event_ics": _ics_for(uid),
                    "if_none_match_star": False,
                },
            )
        assert exc.value.code is ErrorCode.TOOL_DENIED
        # IDs/precondições ausentes: recusa tipada.
        with pytest.raises(EduAgentError) as exc:
            adapter.call_tool("calendar.update", {"uid": uid})
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        # Fluxo permitido: create → read → update → delete.
        created = adapter.call_tool(
            "calendar.create",
            {
                "uid": uid,
                "event_ics": _ics_for(uid),
                "if_none_match_star": True,
            },
        )
        assert created == {"outcome": "APPLIED"}
        read = adapter.call_tool("calendar.read", {"uid": uid})
        assert read is not None and read["etag"].startswith("etag-")
        updated = adapter.call_tool(
            "calendar.update",
            {
                "uid": uid,
                "href": read["href"],
                "event_ics": _ics_for(uid),
                "if_match_etag": read["etag"],
            },
        )
        assert updated == {"outcome": "APPLIED"}
        read2 = adapter.call_tool("calendar.read", {"uid": uid})
        deleted = adapter.call_tool(
            "calendar.delete",
            {
                "uid": uid,
                "href": read2["href"],
                "if_match_etag": read2["etag"],
            },
        )
        assert deleted == {"outcome": "APPLIED"}
        assert adapter.call_tool("calendar.read", {"uid": uid}) is None

    def test_s8b_read_ausente_devolve_null(self):
        adapter = McpCalendarAdapter(
            CaldavConnector(
                CaldavConfig(base_url=BASE_URL),
                transport=FakeCaldavServer().transport,
            )
        )
        assert adapter.call_tool("calendar.read", {"uid": "x"}) is None


class TestAdmissaoIndividual:
    def test_s9_registro_google_nao_admitido(self):
        admission = connector_admission()
        assert admission == dict(CONNECTOR_ADMISSION)
        assert "NÃO ADMITIDO" in admission["google"]
        assert "NÃO realizada" in admission["google"]
        assert admission["caldav"].startswith("ADMITIDO")
        # Construção do conector Google é recusada por código.
        with pytest.raises(EduAgentError) as exc:
            GoogleCalendarConnector()
        assert exc.value.code is ErrorCode.RESOURCE_LIMIT
        assert "CONNECTOR_DISABLED" in exc.value.message

    def test_s9b_admissao_caldav_revalidada_com_redirect_malicioso(self):
        """Correção 016a (achado LUNA-A2): a admissão do CalDAV é revalidada
        com o teste de redirect malicioso no transporte real; o histórico da
        admissão anterior fica preservado no registro."""
        admission = connector_admission()
        assert "revalidado na 016a" in admission["caldav"]
        assert "Histórico da admissão da 016" in admission["caldav"]
        assert "SEM reenviar a credencial Basic" in admission["caldav"]


class TestRedirectMaliciosoCaldav:
    """S10 (correção 016a, achado LUNA-A2): o transporte real do CalDAV não
    segue redirect automático do urllib (que reenviaria a credencial Basic a
    um destino escolhido pelo servidor); cada destino é validado — mesmo
    esquema e mesma autoridade (host:porta) do ``base_url`` — e redirect
    para origem distinta é recusado com ``ConnectorError`` SEM contatar o
    segundo host e SEM reenviar a credencial. Prova por captura em dois
    servidores HTTP locais reais."""

    def _conector(self, base_url: str) -> CaldavConnector:
        transport = make_urllib_transport(
            base_url, "aluno", "segredo-do-aluno", timeout_s=5.0
        )
        return CaldavConnector(
            CaldavConfig(base_url=base_url), transport=transport
        )

    def test_s10_redirect_para_outro_host_recusado_sem_contato_e_sem_credencial(
        self,
    ):
        malicioso = _HttpServerLocal(
            lambda method, path, headers, body: (
                302,
                {},
                b"",
            )
        )
        porta_maliciosa = malicioso.port

        def respond(method, path, headers, body):
            return (
                302,
                {
                    "Location": f"http://127.0.0.1:{porta_maliciosa}/roubo"
                },
                b"",
            )

        servidor = _HttpServerLocal(respond)
        try:
            connector = self._conector(f"{servidor.url}/dav/")
            with pytest.raises(ConnectorError) as exc:
                connector.read_all("calendar.sync")
            assert "origem distinta" in str(exc.value)
            assert "credencial" in str(exc.value)
            # Captura: o primeiro host recebeu EXATAMENTE a requisição
            # autenticada original (credencial confinada à origem configurada)
            # e o segundo host NUNCA foi contatado.
            assert len(servidor.requests_seen) == 1
            metodo, caminho, headers = servidor.requests_seen[0]
            assert metodo == "REPORT"
            assert headers.get("Authorization", "").startswith("Basic ")
            assert malicioso.requests_seen == []
        finally:
            servidor.close()
            malicioso.close()

    def test_s10b_redirect_trocando_esquema_recusado(self):
        porta: dict[str, int] = {}

        def respond(method, path, headers, body):
            # Mesmo host:porta, mas https — esquema distinto do base_url.
            return (
                302,
                {"Location": f"https://127.0.0.1:{porta['valor']}/dav/"},
                b"",
            )

        servidor = _HttpServerLocal(respond)
        porta["valor"] = servidor.port
        try:
            connector = self._conector(f"{servidor.url}/dav/")
            with pytest.raises(ConnectorError) as exc:
                connector.read_all("calendar.sync")
            assert "origem distinta" in str(exc.value)
            # Nenhuma requisição adicional além do REPORT original.
            assert len(servidor.requests_seen) == 1
        finally:
            servidor.close()

    def test_s10c_location_protocol_relative_recusado(self):
        def respond(method, path, headers, body):
            return 302, {"Location": "//evil.exemplo.invalid/roubo"}, b""

        servidor = _HttpServerLocal(respond)
        try:
            connector = self._conector(f"{servidor.url}/dav/")
            with pytest.raises(ConnectorError) as exc:
                connector.read_all("calendar.sync")
            assert "origem distinta" in str(exc.value)
            assert len(servidor.requests_seen) == 1
        finally:
            servidor.close()

    def test_s10d_redirect_mesmo_origem_e_segido(self):
        multistatus = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:multistatus xmlns:d="DAV:" '
            'xmlns:c="urn:ietf:params:xml:ns:caldav">'
            "<d:response><d:href>/dav/evento.ics</d:href>"
            "<d:propstat><d:prop>"
            '<d:getetag>"etag-1"</d:getetag>'
            "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
            "</d:response></d:multistatus>"
        ).encode("utf-8")

        def respond(method, path, headers, body):
            if path == "/dav/":
                return 302, {"Location": "/dav/colecao/"}, b""
            if path == "/dav/colecao/":
                return 207, {"Content-Type": "application/xml"}, multistatus
            raise AssertionError(f"caminho inesperado: {path}")

        servidor = _HttpServerLocal(respond)
        try:
            connector = self._conector(f"{servidor.url}/dav/")
            events = connector.read_all("calendar.sync")
            assert len(events) == 1
            assert events[0].etag == "etag-1"
            # Dois REPORTs: o original e o hop mesmo-origem seguido.
            assert [r[0] for r in servidor.requests_seen] == [
                "REPORT",
                "REPORT",
            ]
        finally:
            servidor.close()


class TestEndurecimentoParseMultistatus:
    """S11 (correção 016a, achados GLM-A1/QW-A2): parse recusa DTD/entidades,
    limita bytes pré-parse (1 MiB, default de ensaio) e o REPORT tem teto de
    corpo (5 MiB, default de ensaio — o §9 NÃO prescreve valor; nunca
    apresentado como resultado medido)."""

    def test_s11_multistatus_com_dtd_e_entidades_recusado(self):
        xml = (
            '<?xml version="1.0"?>'
            "<!DOCTYPE d:multistatus ["
            '<!ENTITY a "aaaaaaaaaaaaaaaaaaaa">'
            "]>"
            '<d:multistatus xmlns:d="DAV:"/>'
        ).encode("utf-8")
        with pytest.raises(ConnectorError) as exc:
            parse_multistatus(xml, BASE_URL)
        assert "DTD" in str(exc.value) or "entidades" in str(exc.value)

    def test_s11b_entidade_no_preambulo_sem_doctype_recusada(self):
        xml = (
            '<?xml version="1.0"?>'
            '<!ENTITY xxe SYSTEM "file:///etc/passwd">'
            '<d:multistatus xmlns:d="DAV:"/>'
        ).encode("utf-8")
        with pytest.raises(ConnectorError):
            parse_multistatus(xml, BASE_URL)

    def test_s11c_bytes_pre_parse_limitados_a_um_mib(self):
        assert MAX_MULTISTATUS_BYTES == 1 * 1024 * 1024  # default de ensaio
        xml = (
            b'<d:multistatus xmlns:d="DAV:">'
            + b"a" * MAX_MULTISTATUS_BYTES
            + b"</d:multistatus>"
        )
        with pytest.raises(ConnectorError) as exc:
            parse_multistatus(xml, BASE_URL)
        assert "excede" in str(exc.value)
        # Limite é default: parâmetro explícito é honrado (ensaio).
        menor = (
            b'<d:multistatus xmlns:d="DAV:">' + b"a" * 2049 + b"</d:multistatus>"
        )
        with pytest.raises(ConnectorError):
            parse_multistatus(menor, BASE_URL, max_bytes=2048)

    def test_s11d_report_com_corpo_acima_do_teto_recusado(self):
        assert MAX_REPORT_BODY_BYTES == 5 * 1024 * 1024  # default de ensaio

        def transport(method, url, body, headers):
            return (
                207,
                {"Content-Type": "application/xml"},
                b"<d:multistatus xmlns:d=\"DAV:\"></d:multistatus>"
                .ljust(MAX_REPORT_BODY_BYTES + 1, b"a"),
            )

        connector = CaldavConnector(
            CaldavConfig(base_url=BASE_URL), transport=transport
        )
        with pytest.raises(ConnectorError) as exc:
            connector.read_all("calendar.sync")
        assert "REPORT" in str(exc.value)
        assert "excede" in str(exc.value)

    def test_s11e_multistatus_legitimo_sem_dtd_continua_ok(self):
        uid = str(_uid(9010))
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:multistatus xmlns:d="DAV:" '
            'xmlns:c="urn:ietf:params:xml:ns:caldav">'
            f"<d:response><d:href>{BASE_URL}{uid}.ics</d:href>"
            "<d:propstat><d:prop>"
            '<d:getetag>"etag-9"</d:getetag>'
            "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
            "</d:response></d:multistatus>"
        ).encode("utf-8")
        entries = parse_multistatus(xml, BASE_URL)
        assert len(entries) == 1
        assert entries[0]["etag"] == "etag-9"


class TestWiringConectorCalendar:
    """S12 (correção 016a, achado QW-A1): o runtime constrói
    ``calendar_connector=build_calendar_connector(effective_config)`` —
    CalDAV configurado chega ao grafo pela superfície CLI/API; sem config,
    ``CONNECTOR_DISABLED`` com ICS/preview (S7 preservado)."""

    def test_s12_config_caldav_presente_chega_ao_grafo(self, tmp_path):
        ctx = RuntimeContext.open(
            tmp_path,
            config={
                "calendar_sync_enabled": True,
                "calendar_sync": {"base_url": BASE_URL},
            },
        )
        try:
            connector = ctx.graph._calendar_connector
            assert isinstance(connector, CaldavConnector)
        finally:
            ctx.close()

    def test_s12_sem_config_conectora_desabilitada_mantida(self, tmp_path):
        ctx = RuntimeContext.open(tmp_path)
        try:
            assert ctx.graph._calendar_connector is None
        finally:
            ctx.close()
        # Comportamento S7 preservado: sem conector, apply mantém
        # ICS/preview e reporta CONNECTOR_DISABLED.
        store, effects, service, confirmation = _confirmed_plan(
            tmp_path / "s7"
        )
        try:
            report = service.apply_plan(
                UID, confirmation.plan_id, connector=None
            )
            assert report.status is SyncOutcome.UNCHANGED
            assert "CONNECTOR_DISABLED" in report.detail
        finally:
            store.close()


# ---------------------------------------------------------------------------
# D — dívida herdada da 014a: reembolso no TIMEOUT pós-consume_llm
# ---------------------------------------------------------------------------


class TestDebitoTimeout014a:
    def test_d1_timeout_antes_do_enqueue_reembolsa_debito(self):
        gate = GenerationGate(object())
        limits = TurnLimits(
            max_llm_calls=2,
            max_tool_calls=2,
            max_graph_steps=2,
            max_repairs_total=1,
            deadline=T0 - timedelta(seconds=1),  # já expirado
            clock=lambda: T0,
        )
        with pytest.raises(EduAgentError) as exc:
            gate.generate(
                limits=limits,
                messages=[{"role": "user", "content": "x"}],
                schema=None,
                sampler=None,
                seed=None,
            )
        assert exc.value.code is ErrorCode.TIMEOUT
        # Discriminante da dívida: débito reembolsado — nada foi gerado.
        assert limits.llm_calls_remaining == 2

    def test_d1b_timeout_durante_fila_continua_sem_reembolso(self):
        """Após enqueue aceito, o débito é legítimo: TIMEOUT do resultado não
        reembolsa (a chamada foi feita) — comportamento anterior preservado."""

        class BackendLento:
            def generate(self, **kwargs):
                time.sleep(0.5)  # excede o llm_timeout_s do gate
                raise AssertionError("não deveria chegar ao resultado")

        gate = GenerationGate(BackendLento(), llm_timeout_s=0.05)
        limits = TurnLimits(
            max_llm_calls=2,
            max_tool_calls=2,
            max_graph_steps=2,
            max_repairs_total=1,
        )
        with pytest.raises(EduAgentError) as exc:
            gate.generate(
                limits=limits,
                messages=[{"role": "user", "content": "x"}],
                schema=None,
                sampler=None,
                seed=None,
            )
        assert exc.value.code is ErrorCode.TIMEOUT
        assert limits.llm_calls_remaining == 1  # chamada consumida


# ---------------------------------------------------------------------------
# Harness mínimo do grafo (rota curate) e do calendário (confirmação)
# ---------------------------------------------------------------------------


def open_curate_stack(
    tmp_path: Path,
    *,
    web_connector: Any | None = None,
    calendar_connector: Any | None = None,
    config: dict | None = None,
) -> SimpleNamespace:
    store = DomainStore.open(tmp_path / "domain.sqlite")
    store.ensure_user(UID)
    checkpointer = SQLiteCheckpointer(tmp_path / "checkpoints.sqlite")
    graph = EduAgentGraph(
        store=store,
        checkpointer=checkpointer,
        config=config,
        clock=lambda: T0,
        web_connector=web_connector,
        calendar_connector=calendar_connector,
        data_root=tmp_path / "data",
    )
    return SimpleNamespace(store=store, graph=graph, checkpointer=checkpointer)


def _insert_demand(store: DomainStore, demand_id: _uuid.UUID) -> None:
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO demands(id, user_id, payload_json, status, "
                "revision) VALUES (?,?,?,'pending',0)",
                (str(demand_id), UID, "{}"),
            )
        ],
    )


def _block(
    n: int, start: datetime, end: datetime, *, demand: int | None = None
) -> ScheduleProposal.PlanBlock:
    return ScheduleProposal.PlanBlock(
        block_id=_uid(n),
        demand_id=_uid(demand if demand is not None else n),
        start_utc=start,
        end_utc=end,
        uid=_uid(9000 + n),
    )


def _proposal(
    blocks: list[ScheduleProposal.PlanBlock],
    *,
    plan_n: int = 1,
    revision: int = 1,
    snapshot: int = 0,
) -> ScheduleProposal:
    return ScheduleProposal(
        plan_id=_uid(plan_n),
        revision=revision,
        snapshot_version=snapshot,
        status=ScheduleProposal.SolverStatus.OPTIMAL,
        blocks=blocks,
        unmet_demands=[],
        diff=ScheduleProposal.PlanDiff(
            added=[b.block_id for b in blocks],
            moved=[],
            removed=[],
            deficit_minutes=0,
        ),
        validation=ScheduleProposal.PlanValidation(
            passed=True,
            verifier_id="schedule_verifier_v1",
            checked_at=T0,
            issues=[],
        ),
        objective="teste 016",
        bound=None,
        explanation="proposta de teste",
    )


def _confirmed_plan(tmp_path: Path):
    """Domínio + confirmação vigente de um plano com um bloco (§15.1)."""
    store = DomainStore.open(tmp_path / "domain.sqlite")
    store.ensure_user(UID)
    effects = EffectsService(store)
    service = CalendarService(store, effects, clock=lambda: T0)
    block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
    _insert_demand(store, block.demand_id)
    result = service.approve_plan(UID, _proposal([block]))
    return store, effects, service, result.confirmation
