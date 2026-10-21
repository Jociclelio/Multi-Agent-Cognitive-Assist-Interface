"""Ponto de entrada do catálogo de skills (revisão offline, mapa §8).

``python -m eduagent.skills --rehash`` regenera ``catalog.json`` — use
SOMENTE em revisão offline de skills (edição de YAML + commit); o runtime
nunca escreve no catálogo (mapa §8: sem autoedição ao vivo).
"""

from eduagent.skills.loader import _main

if __name__ == "__main__":
    raise SystemExit(_main())
