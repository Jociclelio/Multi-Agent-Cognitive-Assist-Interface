"""Catálogo de skills YAML do Tutor (mapa normativo
``fase2/documentos/04_mapa_completo_do_sistema.md``, §8; task 008).

Contrato do mapa §8 implementado aqui:

- **Schema da skill**: ``id, version, tasks, input_schema, preconditions,
  steps, allowed_tools, output_schema, postconditions, stop_conditions,
  max_calls, cases`` — o modelo ``SkillSpec`` é estrito (``extra='forbid'``):
  campo faltante ou desconhecido no YAML é rejeitado no carregamento.
- **Catálogo obrigatório**: explicar (``explain``), pistas
  (``graduated_hint``), quiz, flashcard e autoexplicação (``self_explain``) —
  o carregamento falha tipado se algum faltar.
- **Hash/version registrados**: ``catalog.json`` (registrado no repositório)
  fixa, por skill, o arquivo, a versão e o SHA-256 do ``skill.yaml``; o
  carregamento recalcula o hash e confere contra o registro — divergência é
  erro tipado ``SCHEMA_INVALID``.
- **Alterações só por revisão offline, sem autoedição ao vivo** (§8): o
  carregador é somente leitura e não expõe nenhum caminho de escrita em
  runtime; a única forma de alterar uma skill é editar o ``skill.yaml`` e
  regenerar o registro com a ferramenta offline
  (``python -m eduagent.skills --rehash``), que é uma revisão registrada em
  commit. ``allowed_tools`` é validado contra a tabela de ferramentas do
  mapa §10 — ferramenta desconhecida no YAML é rejeitada.

Nenhuma parte deste módulo executa o Tutor nem chama o modelo: é somente
catálogo (leitura, validação e hash).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

from eduagent.contracts import (
    ErrorCode,
    EduAgentError,
    SenderRole,
    ToolName,
    validate_tool_request,
)

#: Referência de diagnóstico local (mapa §4).
DIAGNOSTIC = "eduagent/skills/loader.py"

#: Diretório padrão do catálogo (o próprio pacote ``eduagent/skills/``).
DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent

#: Nome do arquivo de skill dentro de cada diretório (mapa §3).
SKILL_FILE = "skill.yaml"

#: Nome do registro de hashes/versões (revisão offline, §8).
REGISTRY_FILE = "catalog.json"

#: Versão do schema do registro.
REGISTRY_SCHEMA_VERSION = "1"

#: Catálogo obrigatório do mapa §8: explicar, pistas, quiz, flashcard,
#: autoexplicação (ids de diretório do mapa §3).
MANDATORY_SKILL_IDS: frozenset[str] = frozenset(
    {"explain", "graduated_hint", "quiz", "flashcard", "self_explain"}
)

#: Padrão de ``id`` de skill (mesma forma de ``TutorTurn.skill_id``, §4).
_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"


class SkillSpecError(EduAgentError):
    """Erro tipado do catálogo de skills (sempre diagnóstico local)."""

    def __init__(self, message: str) -> None:
        super().__init__(
            ErrorCode.SCHEMA_INVALID,
            message,
            diagnostic=DIAGNOSTIC,
        )


class SkillCase(BaseModel):
    """Caso de teste declarado na skill (campo ``cases`` do mapa §8)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str = Field(min_length=1, max_length=200)
    input: dict[str, Any] = Field(default_factory=dict)
    expectation: str = Field(min_length=1, max_length=2000)


class SkillSpec(BaseModel):
    """Spec estrita de uma skill YAML — exatamente os campos do mapa §8."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = Field(pattern=_ID_PATTERN)
    version: StrictInt = Field(ge=1)
    tasks: list[str] = Field(min_length=1, max_length=32)
    input_schema: dict[str, Any]
    preconditions: list[str] = Field(max_length=32)
    steps: list[str] = Field(min_length=1, max_length=32)
    allowed_tools: list[ToolName] = Field(default_factory=list, max_length=16)
    output_schema: dict[str, Any]
    postconditions: list[str] = Field(max_length=32)
    stop_conditions: list[str] = Field(min_length=1, max_length=32)
    max_calls: StrictInt | None = Field(default=None, ge=1)
    cases: list[SkillCase] = Field(default_factory=list, max_length=64)

    @field_validator("tasks", "preconditions", "steps", "postconditions",
                     "stop_conditions")
    @classmethod
    def _strings_nonempty(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("itens de lista de texto devem ser não vazios")
        return value

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def _parse_tools(cls, value: Any) -> Any:
        """Aceita strings no YAML e valida contra a tabela de ferramentas do
        mapa §10 no papel do Tutor (as skills do catálogo §8 são skills do
        Tutor): ferramenta inexistente ou não proposável pelo Tutor é
        rejeitada — JSON/declarção correta para ação proibida é negada."""
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, str):
                    raise ValueError(
                        f"allowed_tools espera nomes de ferramenta (str), "
                        f"obteve {item!r}"
                    )
                try:
                    tool = ToolName(item)
                except ValueError as exc:
                    raise ValueError(
                        f"ferramenta desconhecida na tabela do mapa §10: "
                        f"{item!r}"
                    ) from exc
                try:
                    validate_tool_request(tool, SenderRole.TUTOR)
                except EduAgentError as exc:
                    raise ValueError(
                        f"ferramenta {item!r} não pode ser proposta pelo "
                        "Tutor (tabela do mapa §10)"
                    ) from exc
        return value


class SkillCatalog:
    """Catálogo imutável de skills carregadas e conferidas por hash.

    Instâncias são somente leitura: não há método de escrita, e os mapeamentos
    internos são ``MappingProxyType`` — não existe caminho de autoedição ao
    vivo (§8). Novas versões de skill entram apenas por revisão offline
    (edição do YAML + ``--rehash`` + commit).
    """

    def __init__(
        self,
        skills: Mapping[str, SkillSpec],
        hashes: Mapping[str, str],
        directory: Path,
    ) -> None:
        self._skills: Mapping[str, SkillSpec] = MappingProxyType(dict(skills))
        self._hashes: Mapping[str, str] = MappingProxyType(dict(hashes))
        self.directory = directory

    # -- acesso ------------------------------------------------------------

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._skills))

    def get(self, skill_id: str) -> SkillSpec | None:
        return self._skills.get(skill_id)

    def require(self, skill_id: str) -> SkillSpec:
        spec = self._skills.get(skill_id)
        if spec is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"skill '{skill_id}' não existe no catálogo",
                diagnostic=DIAGNOSTIC,
            )
        return spec

    def hash_of(self, skill_id: str) -> str:
        """SHA-256 registrado do ``skill.yaml`` (§8: hash registrado)."""
        digest = self._hashes.get(skill_id)
        if digest is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"skill '{skill_id}' sem hash registrado",
                diagnostic=DIAGNOSTIC,
            )
        return digest

    def summary(self) -> dict[str, dict[str, Any]]:
        """Resumo ``id -> {version, sha256, file}`` para registro no
        manifesto (congelamento é da task 017, mapa §13.10)."""
        return {
            skill_id: {
                "version": self._skills[skill_id].version,
                "sha256": self._hashes[skill_id],
                "file": f"{skill_id}/{SKILL_FILE}",
            }
            for skill_id in sorted(self._skills)
        }

    # -- carregamento (somente leitura) ------------------------------------

    @classmethod
    def load(cls, directory: Path | str | None = None) -> "SkillCatalog":
        """Carrega e valida o catálogo: spec estrita de cada ``skill.yaml``
        + conferência do hash/version contra ``catalog.json``.

        Falha tipada ``SCHEMA_INVALID`` em: YAML inválido, campo faltante/
        desconhecido, ferramenta desconhecida, skill obrigatória ausente,
        arquivo não registrado, hash divergente ou versão divergente —
        alteração de skill sem revisão offline registrada não carrega (§8).
        """
        base = Path(directory) if directory is not None else DEFAULT_SKILLS_DIR
        registry = cls._load_registry(base / REGISTRY_FILE)

        skills: dict[str, SkillSpec] = {}
        hashes: dict[str, str] = {}
        for skill_id, entry in registry.items():
            spec, digest = cls._load_skill(base, skill_id, entry)
            skills[skill_id] = spec
            hashes[skill_id] = digest

        missing = MANDATORY_SKILL_IDS - set(skills)
        if missing:
            raise SkillSpecError(
                "catálogo obrigatório incompleto (mapa §8); ausentes: "
                + ", ".join(sorted(missing))
            )
        return cls(skills, hashes, base)

    # -- internos -----------------------------------------------------------

    @staticmethod
    def _load_registry(path: Path) -> dict[str, dict[str, Any]]:
        if not path.is_file():
            raise SkillSpecError(
                f"registro de skills ausente: {path}; gere-o com a revisão "
                "offline 'python -m eduagent.skills --rehash'"
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SkillSpecError(f"registro de skills ilegível: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema_version") != (
            REGISTRY_SCHEMA_VERSION
        ):
            raise SkillSpecError(
                f"registro de skills com schema_version inesperado em {path}"
            )
        skills = data.get("skills")
        if not isinstance(skills, dict) or not skills:
            raise SkillSpecError("registro de skills sem entradas")
        import re as _re

        for skill_id, entry in skills.items():
            if not isinstance(skill_id, str) or not _re.match(
                _ID_PATTERN, skill_id
            ):
                raise SkillSpecError(f"id de skill inválido no registro: {skill_id!r}")
            if not isinstance(entry, dict):
                raise SkillSpecError(
                    f"entrada do registro de '{skill_id}' não é um objeto"
                )
            for field in ("file", "version", "sha256"):
                if field not in entry:
                    raise SkillSpecError(
                        f"entrada do registro de '{skill_id}' sem '{field}'"
                    )
            if not isinstance(entry["sha256"], str) or not _re.fullmatch(
                r"[0-9a-f]{64}", entry["sha256"]
            ):
                raise SkillSpecError(
                    f"sha256 inválido para '{skill_id}' no registro"
                )
            if not isinstance(entry["version"], int) or entry["version"] < 1:
                raise SkillSpecError(
                    f"version inválida para '{skill_id}' no registro"
                )
            if not isinstance(entry["file"], str) or not entry["file"]:
                raise SkillSpecError(
                    f"file inválido para '{skill_id}' no registro"
                )
        return skills

    @classmethod
    def _load_skill(
        cls, base: Path, skill_id: str, entry: dict[str, Any]
    ) -> tuple[SkillSpec, str]:
        expected_file = f"{skill_id}/{SKILL_FILE}"
        if entry["file"] != expected_file:
            raise SkillSpecError(
                f"registro de '{skill_id}' aponta para {entry['file']!r}; "
                f"esperado {expected_file!r}"
            )
        path = base / skill_id / SKILL_FILE
        if not path.is_file():
            raise SkillSpecError(
                f"skill registrada mas ausente no disco: {path}"
            )
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise SkillSpecError(f"skill ilegível: {path}: {exc}") from exc
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry["sha256"]:
            raise SkillSpecError(
                f"hash de '{skill_id}' diverge do registro "
                f"(registrado {entry['sha256'][:12]}…, atual {digest[:12]}…); "
                "alteração de skill exige revisão offline com 'python -m "
                "eduagent.skills --rehash' e commit (mapa §8: sem autoedição "
                "ao vivo)"
            )
        try:
            data = yaml.safe_load(raw.decode("utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            raise SkillSpecError(f"YAML inválido em {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise SkillSpecError(f"skill {path} não é um mapeamento YAML")
        if data.get("id") != skill_id:
            raise SkillSpecError(
                f"campo id de {path} é {data.get('id')!r}; esperado {skill_id!r}"
            )
        if data.get("version") != entry["version"]:
            raise SkillSpecError(
                f"version de '{skill_id}' no YAML ({data.get('version')!r}) "
                f"diverge do registro ({entry['version']!r}); revise offline"
            )
        try:
            spec = SkillSpec.model_validate(data)
        except Exception as exc:  # pydantic ValidationError e afins
            raise SkillSpecError(
                f"skill '{skill_id}' viola o schema do mapa §8 "
                f"({type(exc).__name__}): {exc}"
            ) from exc
        return spec, digest


# ---------------------------------------------------------------------------
# Ferramenta offline de revisão (regenera catalog.json) — mapa §8
# ---------------------------------------------------------------------------


def rehash(directory: Path | str = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
    """Regenera o registro ``catalog.json`` a partir do disco (revisão
    offline). Valida cada skill contra o schema antes de registrar; retorna o
    resumo escrito. NÃO é chamado em runtime pelo Tutor."""
    base = Path(directory)
    skills: dict[str, dict[str, Any]] = {}
    for skill_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        path = skill_dir / SKILL_FILE
        if not path.is_file():
            continue
        skill_id = skill_dir.name
        raw = path.read_bytes()
        try:
            data = yaml.safe_load(raw.decode("utf-8"))
            spec = SkillSpec.model_validate(data)
        except Exception as exc:
            raise SkillSpecError(
                f"skill '{skill_id}' inválida ao registrar: {exc}"
            ) from exc
        skills[skill_id] = {
            "file": f"{skill_id}/{SKILL_FILE}",
            "version": spec.version,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    payload = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "nota": (
            "Registro de hash/version das skills (mapa §8). Alterações de "
            "skill só por revisão offline: edite o skill.yaml e regenere "
            "este arquivo com 'python -m eduagent.skills --rehash' (mapa §8: "
            "sem autoedição ao vivo)."
        ),
        "skills": skills,
    }
    out = base / REGISTRY_FILE
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Catálogo de skills do Tutor (mapa §8). Use --rehash apenas em "
            "revisão offline de skills."
        )
    )
    parser.add_argument(
        "--rehash",
        action="store_true",
        help="regenera catalog.json a partir dos skill.yaml (revisão offline)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="apenas carrega e valida o catálogo (exit 1 em falha)",
    )
    parser.add_argument(
        "--dir",
        default=str(DEFAULT_SKILLS_DIR),
        help="diretório do catálogo (default: eduagent/skills)",
    )
    args = parser.parse_args(argv)
    try:
        if args.rehash:
            payload = rehash(args.dir)
            print(f"registro regenerado: {len(payload['skills'])} skills")
            return 0
        catalog = SkillCatalog.load(args.dir)
    except EduAgentError as exc:
        print(f"erro: {exc.message}", file=sys.stderr)
        return 1
    if args.check:
        print(f"catálogo ok: {', '.join(catalog.ids())}")
        return 0
    print(json.dumps(catalog.summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
