"""Catálogo de skills YAML do Tutor (mapa normativo
``fase2/documentos/04_mapa_completo_do_sistema.md``, §8; task 008).

Campos obrigatórios de cada ``skill.yaml`` (§8): ``id, version, tasks,
input_schema, preconditions, steps, allowed_tools, output_schema,
postconditions, stop_conditions, max_calls, cases``. Alterações de skill só
por revisão offline (sem autoedição ao vivo): edite o YAML e regenere o
registro com ``python -m eduagent.skills --rehash``.
"""

from eduagent.skills.loader import (
    DEFAULT_SKILLS_DIR,
    MANDATORY_SKILL_IDS,
    SkillCatalog,
    SkillCase,
    SkillSpec,
    SkillSpecError,
    rehash,
)

__all__ = [
    "DEFAULT_SKILLS_DIR",
    "MANDATORY_SKILL_IDS",
    "SkillCatalog",
    "SkillCase",
    "SkillSpec",
    "SkillSpecError",
    "rehash",
]
