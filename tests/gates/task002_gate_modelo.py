"""Gate de aceite do modelo — task 002 (mapa §3.1 e §13.1).

NÃO é a suíte de testes da etapa 8: é o gate de aceite obrigatório da
primeira etapa da sequência do mapa §13, executado uma vez contra o runtime
fixado (fork PrismML-Eng/llama.cpp, tag candidata ``prism-b10743-adfffbe``) e
o candidato ``prism-ml/Ternary-Bonsai-2-27B-gguf`` (revisão
``b072e1d3b35a0a630cece372c2127528e0994386``, arquivo
``Ternary-Bonsai-2-27B-PTQ1_0.gguf``).

Gates obrigatórios (mapa §13.1 / §3.1):
  G1 — carregamento offline: servidor loopback acessível apenas em
       127.0.0.1/localhost (``network_enabled=false``), modelo servido;
  G2 — SHA-256 do arquivo GGUF conferido contra o SHA publicado;
  G3 — tokenizer: /tokenize e /detokenize idempotentes no runtime;
  G4 — geração non-thinking com sampling publicado .7/.8/20/min_p=0
       (presence 1.5 / repeat 1.0 do perfil instruct), texto final não vazio,
       contagens e finish_reason presentes, pensamento separado do texto;
  G5 — JSON schema: resposta conforme schema fixado (só se a capacidade
       estiver verificada; parse/política permanecem obrigatórios);
  G6 — ferramentas negadas: TOOL_DENIED no adaptador;
  G7 — deadline: TIMEOUT tipado;
  G8 — servidor loopback: um slot e fila de quatro; 6º pedido é recusado
       com RESOURCE_LIMIT (verificação de agendamento com adaptador falso
       determinístico — a fila é lógica do EduAgent, não do runtime).

Comparativo (opcional, somente desenvolvimento, NÃO é gate de admissão):
  T1 — perfil thinking 1/.95/20/.05, uma chamada curta, registrado como
       evidência de desenvolvimento (mapa §3.1).

Vereditos:
  MODEL_ADMITTED       — todos os gates obrigatórios passaram (perfil
                         non-thinking);
  MODEL_NOT_ADMITTED   — algum gate obrigatório falhou (sem substituição
                         silenciosa de modelo);
  GATE_NAO_EXECUTADO   — runtime inacessível/impedimento de hardware;
                         registrado como pendente, sem fingir sucesso.

Uso:
  python3 tests/gates/task002_gate_modelo.py \
    --base-url http://127.0.0.1:8093/v1 --model bonsai2-ptq1-0 \
    --gguf runner-llm/models/Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PTQ1_0.gguf \
    --out /tmp/opencode/task002/gate_report.json

Biblioteca padrão apenas; sem acesso à rede externa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eduagent.services.model_adapter import (
    NON_THINKING_SAMPLER,
    THINKING_SAMPLER,
    ErrorCode,
    LoopbackGenerationServer,
    ModelAdapter,
    ModelAdapterError,
    RuntimeCapabilities,
    Sampler,
)

PUBLISHED_SHA256 = "53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3"
PUBLISHED_REVISION = "b072e1d3b35a0a630cece372c2127528e0994386"

SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "resposta": {"type": "string"},
        "confianca": {"type": "string", "enum": ["alta", "media", "baixa"]},
    },
    "required": ["resposta", "confianca"],
}


@dataclass
class Check:
    gid: str
    name: str
    mandatory: bool
    passed: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)


class GateReport:
    def __init__(self) -> None:
        self.checks: list[Check] = []
        self.started = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    def add(self, check: Check) -> Check:
        self.checks.append(check)
        status = {True: "PASS", False: "FAIL", None: "SKIP"}[check.passed]
        print(f"[{status}] {check.gid} — {check.name}")
        if check.details:
            compact = json.dumps(check.details, ensure_ascii=False)[:600]
            print(f"       {compact}")
        return check

    def verdict(self) -> str:
        mandatory = [c for c in self.checks if c.mandatory]
        if any(c.passed is None for c in mandatory):
            return "GATE_NAO_EXECUTADO"
        if all(c.passed for c in mandatory):
            return "MODEL_ADMITTED"
        return "MODEL_NOT_ADMITTED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "gate": "task002-modelo (mapa §3.1, §13.1)",
            "started_at": self.started,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "modelo_candidato": {
                "repo": "prism-ml/Ternary-Bonsai-2-27B-gguf",
                "revision": PUBLISHED_REVISION,
                "arquivo": "Ternary-Bonsai-2-27B-PTQ1_0.gguf",
                "sha256_publicado": PUBLISHED_SHA256,
            },
            "checks": [
                {
                    "id": c.gid,
                    "nome": c.name,
                    "obrigatorio": c.mandatory,
                    "resultado": {True: "PASS", False: "FAIL", None: "SKIP"}[c.passed],
                    "detalhes": c.details,
                }
                for c in self.checks
            ],
            "veredito": self.verdict(),
        }


def is_loopback(base_url: str) -> bool:
    host = base_url.split("//", 1)[-1].split("/", 1)[0].rsplit(":", 1)[0]
    return host in ("127.0.0.1", "localhost", "::1", "[::1]")


def check_sha256(path: Path, expected: str) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 divergente: local={actual} publicado={expected}")
    return actual


def check_json_schema_shape(payload: str, schema: dict[str, Any]) -> list[str]:
    """Validação leve (parse + campos obrigatórios); Pydantic estrito é da task 003."""
    errors: list[str] = []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return [f"JSON inválido: {exc}"]
    if not isinstance(data, dict):
        return ["Resposta não é um objeto JSON."]
    for req in schema.get("required", []):
        if req not in data:
            errors.append(f"Campo obrigatório ausente: {req}")
    props = schema.get("properties", {})
    for key, value in data.items():
        expected = props.get(key, {}).get("type")
        if expected == "string" and not isinstance(value, str):
            errors.append(f"Campo '{key}' deveria ser string.")
    if "confianca" in data and data["confianca"] not in ("alta", "media", "baixa"):
        errors.append("Campo 'confianca' fora do enum.")
    return errors


class FakeAdapter:
    """Adaptador determinístico sem rede, para testar o agendamento do
    servidor loopback (um slot, fila de quatro) sem depender do runtime."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.calls = 0

    def generate(self, messages, schema, sampler, deadline, seed):  # noqa: ANN001
        self.calls += 1
        time.sleep(self.delay)
        return object()  # só sinaliza término; conteúdo não é avaliado aqui


def run(args: argparse.Namespace) -> int:
    report = GateReport()
    capabilities = RuntimeCapabilities(
        json_schema=True,
        json_schema_evidence=(
            "verificada no gate G5 contra o runtime fixado por hash "
            "(imagem sha256:d88136167019e9dfa08e53fd9d962982ce6043f5d3b668bab59acd5f863a6991, "
            "llama-server commit 84445367f, fork PrismML-Eng/llama.cpp)"
        ),
    )
    adapter = ModelAdapter(
        base_url=args.base_url,
        model_id=args.model,
        capabilities=capabilities,
    )

    # G1 — carregamento offline (loopback, modelo servido)
    if not is_loopback(args.base_url):
        report.add(
            Check("G1", "carregamento offline", True, False, {"erro": "base_url não é loopback"})
        )
    else:
        try:
            with urllib.request.urlopen(f"{args.base_url.rstrip('/').removesuffix('/v1')}/health", timeout=10) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            with urllib.request.urlopen(f"{args.base_url}/models", timeout=10) as resp:
                models = json.loads(resp.read().decode("utf-8"))
            served = [m.get("id") for m in models.get("data", [])]
            ok = health.get("status", "ok") in ("ok", True) and args.model in served
            report.add(
                Check(
                    "G1",
                    "carregamento offline (loopback, modelo servido)",
                    True,
                    ok,
                    {"health": health, "modelos_servidos": served, "esperado": args.model},
                )
            )
        except Exception as exc:  # runtime inacessível: impedimento, não falha do modelo
            report.add(
                Check(
                    "G1",
                    "carregamento offline (loopback, modelo servido)",
                    True,
                    None,
                    {"erro": repr(exc), "nota": "runtime inacessível — gate não executado"},
                )
            )

    if report.checks[-1].passed is None:
        return finish(report, args, extra={"impedimento": "runtime inacessível"})

    # G2 — SHA-256 do GGUF conferido
    try:
        actual = check_sha256(Path(args.gguf), PUBLISHED_SHA256)
        report.add(
            Check("G2", "SHA-256 do GGUF conferido contra o publicado", True, True, {"sha256": actual})
        )
    except Exception as exc:
        report.add(Check("G2", "SHA-256 do GGUF conferido contra o publicado", True, False, {"erro": str(exc)}))

    # G3 — tokenizer (rotas /tokenize e /detokenize ficam na raiz do servidor)
    try:
        root = args.base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[: -len("/v1")]
        content = "Citação resolvível: [doc@1:p3:b7] e prazo 15/03/2026."
        req = urllib.request.Request(
            f"{root}/tokenize",
            data=json.dumps({"content": content}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            tokens = json.loads(resp.read().decode("utf-8")).get("tokens", [])
        req = urllib.request.Request(
            f"{root}/detokenize",
            data=json.dumps({"tokens": tokens}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            round_trip = json.loads(resp.read().decode("utf-8")).get("content", "")
        ok = len(tokens) > 0 and round_trip == content
        report.add(
            Check(
                "G3",
                "tokenizer: /tokenize + /detokenize idempotentes",
                True,
                ok,
                {"n_tokens": len(tokens), "round_trip_igual": round_trip == content},
            )
        )
    except Exception as exc:
        report.add(Check("G3", "tokenizer", True, False, {"erro": repr(exc)}))

    # G4 — geração non-thinking com o sampling publicado
    try:
        result = adapter.generate(
            messages=[
                {"role": "system", "content": "Você é um assistente conciso."},
                {"role": "user", "content": "Responda em uma frase: o que é um prazo absoluto?"},
            ],
            schema=None,
            sampler=Sampler(
                temperature=NON_THINKING_SAMPLER.temperature,
                top_p=NON_THINKING_SAMPLER.top_p,
                top_k=NON_THINKING_SAMPLER.top_k,
                min_p=NON_THINKING_SAMPLER.min_p,
                presence_penalty=NON_THINKING_SAMPLER.presence_penalty,
                repeat_penalty=NON_THINKING_SAMPLER.repeat_penalty,
                max_tokens=64,  # resposta de uma frase; orçamento do gate em CPU
                thinking=False,
            ),
            deadline=float(args.deadline_s),
            seed=args.seed,
        )
        ok = (
            result.finish_reason == "stop"
            and bool(result.text.strip())
            and result.prompt_tokens > 0
            and result.completion_tokens > 0
        )
        report.add(
            Check(
                "G4",
                "non-thinking .7/.8/20/min_p=0: texto final, contagens, finish_reason",
                True,
                ok,
                {
                    "finish_reason": result.finish_reason,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "thinking_separado": result.thinking is None or result.thinking not in result.text,
                    "texto_final": result.text[:300],
                },
            )
        )
    except ModelAdapterError as exc:
        report.add(Check("G4", "non-thinking", True, False, {"erro": exc.to_dict()}))

    # G5 — JSON schema
    if capabilities.json_schema:
        try:
            result = adapter.generate(
                messages=[
                    {"role": "user", "content": "Responda em JSON com os campos 'resposta' e 'confianca'."},
                ],
                schema=SIMPLE_SCHEMA,
                sampler=Sampler(
                    temperature=NON_THINKING_SAMPLER.temperature,
                    top_p=NON_THINKING_SAMPLER.top_p,
                    top_k=NON_THINKING_SAMPLER.top_k,
                    min_p=NON_THINKING_SAMPLER.min_p,
                    presence_penalty=NON_THINKING_SAMPLER.presence_penalty,
                    repeat_penalty=NON_THINKING_SAMPLER.repeat_penalty,
                    max_tokens=64,  # JSON de dois campos; orçamento do gate em CPU
                    thinking=False,
                ),
                deadline=float(args.deadline_s),
                seed=args.seed,
            )
            errors = check_json_schema_shape(result.text, SIMPLE_SCHEMA)
            report.add(
                Check(
                    "G5",
                    "JSON schema: resposta conforme schema",
                    True,
                    not errors,
                    {"erros": errors, "resposta": result.text[:300]},
                )
            )
        except ModelAdapterError as exc:
            report.add(Check("G5", "JSON schema", True, False, {"erro": exc.to_dict()}))

    # G6 — ferramentas negadas
    try:
        adapter.generate(
            messages=[{"role": "tool", "content": "resultado"}],
            schema=None,
            sampler=NON_THINKING_SAMPLER,
            deadline=5.0,
            seed=None,
        )
        report.add(Check("G6", "ferramentas negadas (TOOL_DENIED)", True, False, {"erro": "TOOL_DENIED não levantado"}))
    except ModelAdapterError as exc:
        report.add(
            Check(
                "G6",
                "ferramentas negadas (TOOL_DENIED)",
                True,
                exc.code is ErrorCode.TOOL_DENIED,
                {"codigo": exc.code.value},
            )
        )

    # G7 — deadline
    try:
        adapter.generate(
            messages=[{"role": "user", "content": "ok?"}],
            schema=None,
            sampler=Sampler(temperature=0.7, top_p=0.8, top_k=20, min_p=0.0, max_tokens=8, thinking=False),
            deadline=0.0,
            seed=None,
        )
        report.add(Check("G7", "deadline expirado -> TIMEOUT", True, False, {"erro": "TIMEOUT não levantado"}))
    except ModelAdapterError as exc:
        report.add(
            Check(
                "G7",
                "deadline expirado -> TIMEOUT",
                True,
                exc.code is ErrorCode.TIMEOUT,
                {"codigo": exc.code.value},
            )
        )

    # G8 — um slot e fila de quatro (agendamento lógico, adaptador falso)
    try:
        fake = FakeAdapter(delay=0.1)
        server = LoopbackGenerationServer(fake, queue_size=4)
        futures = []
        rejected = None
        for i in range(6):
            try:
                futures.append(
                    server.submit(
                        messages=[{"role": "user", "content": f"p{i}"}],
                        schema=None,
                        sampler=NON_THINKING_SAMPLER,
                        deadline=5.0,
                        seed=None,
                    )
                )
            except ModelAdapterError as exc:
                rejected = exc
        for f in futures:
            f.result(timeout=30)
        server.close()
        ok = rejected is not None and rejected.code is ErrorCode.RESOURCE_LIMIT and len(futures) == 5
        report.add(
            Check(
                "G8",
                "servidor loopback: 1 slot + fila de 4; 6º pedido recusado (RESOURCE_LIMIT)",
                True,
                ok,
                {"aceitos": len(futures), "recusado_com": rejected.code.value if rejected else None},
            )
        )
    except Exception as exc:
        report.add(Check("G8", "servidor loopback (fila)", True, False, {"erro": repr(exc)}))

    # T1 — comparativo thinking (opcional, somente desenvolvimento)
    if args.thinking:
        try:
            result = adapter.generate(
                messages=[{"role": "user", "content": "Responda em uma frase: 2+2?"}],
                schema=None,
                sampler=Sampler(
                    temperature=THINKING_SAMPLER.temperature,
                    top_p=THINKING_SAMPLER.top_p,
                    top_k=THINKING_SAMPLER.top_k,
                    min_p=THINKING_SAMPLER.min_p,
                    max_tokens=256,
                    thinking=True,
                ),
                deadline=float(args.deadline_s),
                seed=args.seed,
            )
            report.add(
                Check(
                    "T1",
                    "comparativo thinking 1/.95/20/.05 (desenvolvimento; NÃO é gate)",
                    False,
                    bool(result.text.strip()) or bool((result.thinking or "").strip()),
                    {
                        "finish_reason": result.finish_reason,
                        "completion_tokens": result.completion_tokens,
                        "pensou": bool((result.thinking or "").strip()),
                    },
                )
            )
        except ModelAdapterError as exc:
            report.add(Check("T1", "comparativo thinking", False, False, {"erro": exc.to_dict()}))

    return finish(report, args)


def finish(report: GateReport, args: argparse.Namespace, extra: dict[str, Any] | None = None) -> int:
    payload = report.to_dict()
    if extra:
        payload.update(extra)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    verdict = payload["veredito"]
    print(f"\nVEREDITO: {verdict}")
    print(f"Relatório: {out}")
    if verdict == "MODEL_ADMITTED":
        return 0
    if verdict == "MODEL_NOT_ADMITTED":
        return 1
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8079/v1")
    parser.add_argument("--model", default="bonsai2-ptq1-0")
    parser.add_argument(
        "--gguf",
        default="runner-llm/models/Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PTQ1_0.gguf",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--deadline-s", type=int, default=90, help="default de ensaio do mapa §3")
    parser.add_argument("--thinking", action="store_true", help="comparativo thinking (desenvolvimento)")
    parser.add_argument("--out", default="/tmp/opencode/task002/gate_report.json")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
