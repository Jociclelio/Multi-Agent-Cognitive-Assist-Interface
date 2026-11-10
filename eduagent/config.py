"""Configuração local e resolução automática de fuso horário (mapa §3, Fase 3).

Implementa a resolução automática da timezone a partir do ambiente/sistema
operacional do usuário, com fallback interativo (pergunta ao estudante na CLI
ou na Interface Gráfica Local) quando a detecção automática não puder
determinar um fuso horário IANA específico.

Invariantes preservadas:
- ``manifest.json`` permanece congelado (task 017, G-2);
- Toda string de fuso horário é validada contra ``zoneinfo.ZoneInfo`` (IANA);
- Caso o sistema operacional reporte apenas ``UTC``/``Etc/UTC`` genérico (ex.:
  containers Linux sem TZ configurado) e ``ignore_generic_utc=True``, a
  detecção sinaliza ausência de fuso local específico para acionar o fallback
  (navegador ou pergunta explícita ao usuário).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from eduagent.contracts import EduAgentError, ErrorCode

DIAGNOSTIC = "eduagent/config.py"

DEFAULT_FALLBACK_TIMEZONE = "America/Sao_Paulo"

_GENERIC_UTC_NAMES = frozenset({"UTC", "Etc/UTC", "Etc/GMT", "GMT", "Z", "Universal"})

_ABBR_TO_IANA: dict[str, str] = {
    "BRT": "America/Sao_Paulo",
    "BRST": "America/Sao_Paulo",
    "-03": "America/Sao_Paulo",
    "-0300": "America/Sao_Paulo",
    "-03:00": "America/Sao_Paulo",
    "AMT": "America/Manaus",
    "-04": "America/Manaus",
    "-0400": "America/Manaus",
    "-04:00": "America/Manaus",
    "ACT": "America/Rio_Branco",
    "-05": "America/Rio_Branco",
    "FNT": "America/Noronha",
    "-02": "America/Noronha",
}


def validate_iana_timezone(value: str | None) -> str | None:
    """Valida e normaliza um identificador IANA de fuso horário.

    Levanta ``EduAgentError(ErrorCode.SCHEMA_INVALID)`` se ``value`` for uma
    string não vazia inválida na base IANA (``zoneinfo.ZoneInfo``).
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in ("null", "none", "auto"):
        return None
    if cleaned in _ABBR_TO_IANA:
        cleaned = _ABBR_TO_IANA[cleaned]
    try:
        ZoneInfo(cleaned)
    except (ZoneInfoNotFoundError, KeyError, ValueError) as exc:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"fuso horário IANA inválido: {value!r} (ex.: 'America/Sao_Paulo')",
            diagnostic=DIAGNOSTIC,
        ) from exc
    return cleaned


def _extract_zoneinfo_from_path(path_str: str) -> str | None:
    """Extrai o nome IANA de um caminho ``.../zoneinfo/<Região>/<Cidade>``."""
    marker = "zoneinfo/"
    normalized = path_str.replace("\\", "/")
    idx = normalized.find(marker)
    if idx < 0:
        return None
    candidate = normalized[idx + len(marker) :].strip("/")
    if not candidate or candidate.startswith("posix/") or candidate.startswith("right/"):
        for prefix in ("posix/", "right/"):
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix) :]
    try:
        return validate_iana_timezone(candidate)
    except EduAgentError:
        return None


def detect_system_timezone(
    *,
    env: Mapping[str, str] | None = None,
    etc_timezone_path: Path = Path("/etc/timezone"),
    etc_localtime_path: Path = Path("/etc/localtime"),
    ignore_generic_utc: bool = True,
) -> tuple[str | None, str]:
    """Detecta automaticamente o fuso horário padrão do sistema do usuário.

    Ordem de inspeção:
    1. Variáveis de ambiente ``EDUAGENT_TIMEZONE`` e ``TZ``;
    2. Arquivo ``/etc/timezone`` (sistemas Debian/Ubuntu);
    3. Symlink ``/etc/localtime`` apontando para ``.../zoneinfo/...``;
    4. ``datetime.now().astimezone().tzinfo`` (chave IANA, abreviação ou offset).

    Retorna ``(timezone_iana, source)`` onde ``source`` descreve a origem
    (``"env"``, ``"etc_timezone"``, ``"etc_localtime"``, ``"os_astimezone"``
    ou ``"unresolved"``).
    """
    environ = env if env is not None else os.environ

    # 1. Variáveis de ambiente explícitas
    for var_name in ("EDUAGENT_TIMEZONE", "TZ"):
        raw_env = (environ.get(var_name) or "").strip()
        if not raw_env:
            continue
        if raw_env.startswith(":"):
            raw_env = raw_env[1:].strip()
        from_path = _extract_zoneinfo_from_path(raw_env)
        candidate = from_path or raw_env
        try:
            validated = validate_iana_timezone(candidate)
        except EduAgentError:
            validated = None
        if validated:
            if ignore_generic_utc and validated in _GENERIC_UTC_NAMES and var_name == "TZ":
                continue
            return validated, "env"

    # 2. /etc/timezone
    try:
        if etc_timezone_path.is_file():
            raw_etc = etc_timezone_path.read_text(encoding="utf-8", errors="ignore").strip()
            if raw_etc:
                validated = validate_iana_timezone(raw_etc)
                if validated and not (ignore_generic_utc and validated in _GENERIC_UTC_NAMES):
                    return validated, "etc_timezone"
    except (OSError, EduAgentError):
        pass

    # 3. /etc/localtime symlink
    try:
        if etc_localtime_path.exists() or etc_localtime_path.is_symlink():
            resolved = os.path.realpath(str(etc_localtime_path))
            extracted = _extract_zoneinfo_from_path(resolved)
            if extracted and not (ignore_generic_utc and extracted in _GENERIC_UTC_NAMES):
                return extracted, "etc_localtime"
    except OSError:
        pass

    # 4. datetime.now().astimezone().tzinfo
    try:
        local_dt = datetime.now().astimezone()
        tz = local_dt.tzinfo
        if tz is not None:
            key = getattr(tz, "key", None)
            if isinstance(key, str) and key.strip():
                validated = validate_iana_timezone(key)
                if validated and not (ignore_generic_utc and validated in _GENERIC_UTC_NAMES):
                    return validated, "os_astimezone"
            tz_label = local_dt.strftime("%Z").strip()
            if tz_label in _ABBR_TO_IANA:
                return _ABBR_TO_IANA[tz_label], "os_astimezone"
            offset_str = local_dt.strftime("%z").strip()
            if offset_str in _ABBR_TO_IANA:
                return _ABBR_TO_IANA[offset_str], "os_astimezone"
            if not ignore_generic_utc and tz_label in _GENERIC_UTC_NAMES:
                return "UTC", "os_astimezone"
    except (EduAgentError, ValueError, OSError):
        pass

    return None, "unresolved"


def prompt_user_timezone(
    *,
    input_fn: Callable[[str], str] | None = None,
    output_stream: Any = None,
    default_timezone: str = DEFAULT_FALLBACK_TIMEZONE,
) -> str | None:
    """Pergunta interativamente ao usuário qual fuso horário IANA utilizar (fallback).

    Se a entrada padrão não for interativa e ``input_fn`` não tiver sido
    injetada, retorna ``None`` sem bloquear.
    """
    if input_fn is None:
        if not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
            return None
        reader = input
    else:
        reader = input_fn

    out = output_stream if output_stream is not None else sys.stderr
    prompt_msg = (
        "Não foi possível detectar automaticamente o fuso horário do sistema.\n"
        f"Informe o fuso horário IANA a utilizar [padrão: {default_timezone}]: "
    )
    try:
        raw = reader(prompt_msg)
    except (EOFError, KeyboardInterrupt):
        return None
    choice = (raw or "").strip() or default_timezone
    try:
        return validate_iana_timezone(choice)
    except EduAgentError as exc:
        if out is not None and hasattr(out, "write"):
            out.write(f"Aviso: {exc.message}\n")
        return None


def resolve_timezone(
    configured_tz: str | None = None,
    *,
    user_tz: str | None = None,
    cli_tz: str | None = None,
    auto_detect: bool = True,
    ignore_generic_utc: bool = True,
    prompt_fallback: bool = False,
    input_fn: Callable[[str], str] | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[str | None, str]:
    """Resolve o fuso horário efetivo com decisão automática e fallback.

    Prioridade de resolução:
    1. ``cli_tz`` (flag explícita ``--timezone`` na invocação atual);
    2. ``user_tz`` (fuso persistido na tabela ``users.timezone`` do usuário);
    3. ``configured_tz`` (valor explícito em ``config/default.yaml``);
    4. Detecção automática do sistema operacional (``detect_system_timezone``);
    5. Fallback interativo perguntando ao usuário (``prompt_user_timezone``),
       quando ``prompt_fallback=True``.

    Retorna ``(timezone_iana_ou_none, fonte_da_decisao)``.
    """
    if cli_tz is not None and str(cli_tz).strip().lower() not in ("", "auto", "null", "none"):
        validated = validate_iana_timezone(cli_tz)
        if validated:
            return validated, "cli_arg"

    if user_tz is not None and str(user_tz).strip().lower() not in ("", "auto", "null", "none"):
        try:
            validated = validate_iana_timezone(user_tz)
            if validated:
                return validated, "user_profile"
        except EduAgentError:
            pass

    if configured_tz is not None and str(configured_tz).strip().lower() not in (
        "",
        "auto",
        "null",
        "none",
    ):
        validated = validate_iana_timezone(configured_tz)
        if validated:
            return validated, "config_file"

    if auto_detect:
        detected, det_source = detect_system_timezone(
            env=env, ignore_generic_utc=ignore_generic_utc
        )
        if detected:
            return detected, f"system_auto:{det_source}"

    if prompt_fallback:
        prompted = prompt_user_timezone(input_fn=input_fn)
        if prompted:
            return prompted, "user_prompt"

    return None, "unresolved"


__all__ = [
    "DEFAULT_FALLBACK_TIMEZONE",
    "detect_system_timezone",
    "prompt_user_timezone",
    "resolve_timezone",
    "validate_iana_timezone",
]
