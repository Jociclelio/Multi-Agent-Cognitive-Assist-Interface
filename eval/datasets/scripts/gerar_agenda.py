#!/usr/bin/env python3
"""Gerador deterministico das instancias sinteticas de agenda (etapa 6, task 002).

Gera, com seed mestre fixa (0) e somente biblioteca padrao:

  - agenda/pequenas.jsonl : 100 instancias pequenas (10 familias de parametros
    x 10 instancias), split 40/20/40 por familia inteira (4 dev / 2 val /
    4 test), com viabilidade decidida de forma EXATA por verificador EDF para
    tarefas unitarias (chunks de 30 min, liberacao 0).
  - agenda/borda.jsonl    : 6 casos de borda estruturais (2 por split),
    correspondendo as perturbacoes de F13 (protocolo de avaliacao, secao 4).

Os arquivos sao SINTETICOS: nao derivam do corpus restrito (uso privado, fora
do Git), nao representam dados coletados e sao publicaveis conforme a decisao
D2 da task 001 (hashes, IDs, manifestos e exemplos sinteticos). A execucao dos
mecanismos por celula pertence a etapa 7 e a implementacao do testbed a etapa 8.

Modelo da instancia (compativel com o protocolo, secao 2, e com o mapa da
etapa 8, secao 12): grade de 7 dias, slots de 30 min de 00:00 a 24:00 sem
cruzar meia-noite; janelas de disponibilidade por dia; limite diario de
minutos; atividades com duracao, prazo (dia, minuto), prioridade e
dependencias (ausentes nas pequenas). A viabilidade e decidida pelo seguinte
teorema classico de escalonamento: para tarefas unitarias com liberacao 0,
prazos individuais e perfil arbitrario de capacidade (janelas + limite diario),
ordenar os chunks por prazo e alocar cada um no slot livre mais cedo com
termino <= prazo decide a viabilidade exatamente (argumento de troca: se existe
cronograma viavel, a atribuicao gulosa por prazo mais cedo tambem existe).

O valor de "otimo" e afirmado apenas por forca de construcao na familia
f05-demanda-total (demanda igual a capacidade obriga todo slot usavel a ser
ocupado, logo o makespan e forcado); nas demais familias registra-se o
cronograma de referencia EDF sem alegar minimo global.

Uso: python3 eval/datasets/scripts/gerar_agenda.py
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SEED_MESTRE = 0
DIAS = 7
SLOT = 30
LIMITE_PADRAO = 480

# Familias de parametros: nome -> (split, parametros de geracao).
# A familia INTEIRA vai para um unico split (nunca repartir parentes).
FAMILIAS = {
    "f01-janela-unica": "desenvolvimento",
    "f02-duas-janelas": "desenvolvimento",
    "f03-densidade-baixa": "desenvolvimento",
    "f04-densidade-alta": "desenvolvimento",
    "f05-demanda-total": "validacao",
    "f06-prazos-justos": "validacao",
    "f07-limite-diario-ativo": "teste",
    "f08-inviavel-marginal": "teste",
    "f09-multi-atividade": "teste",
    "f10-janelas-esparsas": "teste",
}

PARAMS = {
    "f01-janela-unica": dict(dias=list(range(7)), jan_por_dia=1, comp=(8, 12),
                             dens=(0.30, 0.50), folga=(1, 3), n_ativ=(2, 3)),
    "f02-duas-janelas": dict(dias=list(range(5)), jan_por_dia=2, comp=(4, 7),
                             dens=(0.45, 0.65), folga=(1, 3), n_ativ=(3, 4)),
    "f03-densidade-baixa": dict(dias=list(range(7)), jan_por_dia=1, comp=(8, 12),
                                dens=(0.20, 0.35), folga=(2, 4), n_ativ=(2, 4)),
    "f04-densidade-alta": dict(dias=list(range(5)), jan_por_dia=2, comp=(4, 7),
                               dens=(0.75, 0.90), folga=(0, 1), n_ativ=(3, 4)),
    "f05-demanda-total": dict(dias=list(range(4)), jan_por_dia=2, comp=(4, 6),
                              dens=(1.0, 1.0), folga=(1, 2), n_ativ=(3, 4)),
    "f06-prazos-justos": dict(dias=list(range(6)), jan_por_dia=1, comp=(6, 9),
                              dens=(0.50, 0.70), folga=(0, 0), n_ativ=(2, 4)),
    "f07-limite-diario-ativo": dict(dias=list(range(6)), jan_por_dia=1, comp=(8, 12),
                                    dens=(0.55, 0.75), folga=(0, 1), n_ativ=(2, 4),
                                    limite_ativo=True),
    "f08-inviavel-marginal": dict(dias=list(range(5)), jan_por_dia=1, comp=(6, 8),
                                  n_ativ=(3, 4), inviavel=True),
    "f09-multi-atividade": dict(dias=list(range(7)), jan_por_dia=1, comp=(5, 8),
                                dens=(0.40, 0.60), folga=(1, 2), n_ativ=(4, 5)),
    "f10-janelas-esparsas": dict(dias=[0, 2, 4, 6], jan_por_dia=1, comp=(10, 14),
                                 dens=(0.40, 0.60), folga=(2, 4), n_ativ=(2, 4)),
}

BORDA_POR_SPLIT = {"desenvolvimento": 2, "validacao": 2, "teste": 2}


def repartir(total: int, partes: int, rng: random.Random) -> list[int]:
    """Composicao aleatoria de `total` em `partes` partes inteiras >= 1."""
    cortes = sorted(rng.sample(range(1, total), partes - 1)) if partes > 1 else []
    pedacos = []
    anterior = 0
    for corte in cortes + [total]:
        pedacos.append(corte - anterior)
        anterior = corte
    return pedacos


def slots_de(janelas: list[dict]) -> list[tuple[int, int]]:
    return sorted({(j["dia"], s) for j in janelas
                   for s in range(j["inicio_min"], j["fim_min"], SLOT)})


def gera_janelas(rng: random.Random, dias: list[int], jan_por_dia: int,
                 comp: tuple[int, int]) -> list[dict]:
    """Janelas disjuntas dentro de cada dia (sem sobreposicao)."""
    janelas: list[dict] = []
    for d in dias:
        do_dia: list[dict] = []
        for _ in range(jan_por_dia):
            for _tentativa in range(64):
                comp_slots = rng.randint(*comp)
                inicio = rng.randrange(0, (24 * 60) // SLOT - comp_slots + 1) * SLOT
                fim = inicio + comp_slots * SLOT
                if all(fim <= e["inicio_min"] or e["fim_min"] <= inicio for e in do_dia):
                    do_dia.append({"dia": d, "inicio_min": inicio, "fim_min": fim})
                    break
            else:
                # varredura deterministica pela primeira posicao livre do dia
                comp_slots = rng.randint(*comp)
                for inicio in range(0, (24 * 60) // SLOT - comp_slots + 1):
                    inicio *= SLOT
                    fim = inicio + comp_slots * SLOT
                    if all(fim <= e["inicio_min"] or e["fim_min"] <= inicio for e in do_dia):
                        do_dia.append({"dia": d, "inicio_min": inicio, "fim_min": fim})
                        break
        janelas.extend(do_dia)
    return janelas


def edf_verifica(janelas: list[dict], atividades: list[dict],
                 limite_diario: int) -> tuple[bool, list[dict] | None]:
    """Viabilidade exata por EDF para chunks unitarios (ver docstring)."""
    chunks: list[tuple[int, str]] = []
    for a in atividades:
        if a["duracao_min"] % SLOT != 0:
            raise ValueError("pequenas usam duracoes multiplas de 30 min")
        if a.get("depende_de"):
            raise ValueError("pequenas nao possuem dependencias")
        prazo = a["prazo"]
        pabs = prazo["dia"] * 1440 + prazo["minuto"]
        chunks.extend([(pabs, a["id"])] * (a["duracao_min"] // SLOT))
    chunks.sort(key=lambda c: (c[0], c[1]))
    slots = slots_de(janelas)
    usado: set[tuple[int, int]] = set()
    uso: dict[int, int] = {}
    cronograma: list[dict] = []
    for pabs, atividade in chunks:
        colocado = None
        for (d, s) in slots:
            if (d, s) in usado:
                continue
            if uso.get(d, 0) + SLOT > limite_diario:
                continue
            if d * 1440 + s + SLOT > pabs:
                break  # slots ordenados: nenhum posterior termina antes do prazo
            usado.add((d, s))
            uso[d] = uso.get(d, 0) + SLOT
            colocado = (d, s)
            break
        if colocado is None:
            return False, None
        d, s = colocado
        cronograma.append({"atividade": atividade, "dia": d,
                           "inicio_min": s, "fim_min": s + SLOT})
    return True, cronograma


def gera_pequena(familia: str, indice: int) -> dict:
    p = PARAMS[familia]
    seed = SEED_MESTRE * 1_000_000 + list(FAMILIAS).index(familia) * 1000 + indice
    rng = random.Random(seed)

    janelas = gera_janelas(rng, p["dias"], p["jan_por_dia"], p["comp"])

    capacidade_slots = sum((j["fim_min"] - j["inicio_min"]) // SLOT for j in janelas)
    assert capacidade_slots == len(slots_de(janelas)), "janelas sobrepostas"

    if p.get("inviavel"):
        demanda_slots = capacidade_slots + 1  # excede a capacidade em 1 slot
    else:
        demanda_slots = max(2, round(capacidade_slots * rng.uniform(*p["dens"])))

    n_ativ = rng.randint(*p["n_ativ"])
    demanda_slots = max(demanda_slots, n_ativ)
    duracoes = repartir(demanda_slots, n_ativ, rng)
    atividades = [
        {"id": f"a{k + 1}", "duracao_min": dur * SLOT,
         "prazo": {"dia": DIAS - 1, "minuto": 1440 - SLOT},
         "prioridade": rng.randint(1, 3), "depende_de": []}
        for k, dur in enumerate(duracoes)
    ]

    limite = LIMITE_PADRAO
    cronograma: list[dict] | None = None
    otimo_por_construcao = False
    makespan_minimo = None

    if p.get("inviavel"):
        ultimo_dia = max(j["dia"] for j in janelas)
        fim_ultima = max(j["fim_min"] for j in janelas if j["dia"] == ultimo_dia)
        for a in atividades:
            a["prazo"] = {"dia": ultimo_dia, "minuto": fim_ultima}
    else:
        ordem = list(range(n_ativ))
        rng.shuffle(ordem)
        slots = slots_de(janelas)
        usado: set[tuple[int, int]] = set()
        uso: dict[int, int] = {}
        fim_ativ: dict[int, tuple[int, int]] = {}
        for oi in ordem:
            restante = duracoes[oi]
            for (d, s) in slots:
                if restante == 0:
                    break
                if (d, s) in usado or uso.get(d, 0) + SLOT > limite:
                    continue
                usado.add((d, s))
                uso[d] = uso.get(d, 0) + SLOT
                fim_ativ[oi] = (d, s + SLOT)
                restante -= 1
            assert restante == 0, "demanda <= capacidade por construcao"
        folga_min = rng.randint(*p["folga"]) * SLOT
        teto = max(j["dia"] * 1440 + j["fim_min"] for j in janelas)
        for oi, a in enumerate(atividades):
            d, m = fim_ativ[oi]
            absmin = min(d * 1440 + m + folga_min, teto)
            a["prazo"] = {"dia": absmin // 1440, "minuto": absmin % 1440}
        if p.get("limite_ativo"):
            limite = max(uso.values())  # ativo no dia mais carregado da referencia

    viavel, cronograma = edf_verifica(janelas, atividades, limite)
    assert viavel == (not p.get("inviavel")), "construcao e verificador discordam"

    if p.get("inviavel"):
        assert cronograma is None
    else:
        # demanda > capacidade nunca ocorre aqui; para f05 (demanda == capacidade)
        # todo slot usavel e obrigatorio, logo o makespan e forcado por construcao.
        if abs(demanda_slots - capacidade_slots) == 0:
            otimo_por_construcao = True
            makespan_minimo = max(d * 1440 + s + SLOT for (d, s) in slots_de(janelas))
            assert max(c["dia"] * 1440 + c["fim_min"] for c in cronograma) == makespan_minimo

    instancia = {
        "id": f"agenda-pequena-{familia}-{indice:02d}",
        "conjunto": "agenda",
        "tipo": "pequena",
        "familia_parametros": familia,
        "split": FAMILIAS[familia],
        "origem": "sintetico",
        "geracao": {"script": "eval/datasets/scripts/gerar_agenda.py",
                    "seed_mestre": SEED_MESTRE, "seed_instancia": seed},
        "grade": {"dias": DIAS, "slot_min": SLOT, "primeiro_slot": "00:00",
                  "ultimo_slot": "24:00", "cruza_meia_noite": False},
        "zona": None,
        "zona_nota": "timezone da v0.1 pendente de confirmacao (plano 04); "
                     "janelas em horario local de parede",
        "janelas": janelas,
        "limite_diario_min": limite,
        "atividades": atividades,
        "esperado": {
            "viavel": viavel,
            "metodo": "edf-chunks-unitarios",
            "exatidao": "viabilidade exata (argumento de troca; chunks unitarios, "
                        "liberacao 0, perfil arbitrario de capacidade)",
            "cronograma_referencia": cronograma,
            "makespan_minimo": makespan_minimo,
            "otimo_por_construcao": otimo_por_construcao,
        },
    }
    return instancia


def borda_split(caso: dict) -> str:
    return caso["split"]


def casos_borda() -> list[dict]:
    """Casos de borda estruturais (2 por split), ancorados em F13 (protocolo
    secao 4: zona DST, prazo meio-slot, duracao 17 min, ciclo, UNKNOWN) e nas
    regras do mapa da etapa 8, secao 12. Verificacao estrutural ou por
    construcao; a execucao do mecanismo pertence as etapas 7/8."""
    base = {
        "conjunto": "agenda",
        "tipo": "borda",
        "origem": "estrutural",
        "geracao": {"script": "eval/datasets/scripts/gerar_agenda.py",
                    "seed_mestre": SEED_MESTRE, "seed_instancia": None},
        "grade": {"dias": DIAS, "slot_min": SLOT, "primeiro_slot": "00:00",
                  "ultimo_slot": "24:00", "cruza_meia_noite": False},
        "zona": None,
        "zona_nota": "timezone da v0.1 pendente de confirmacao (plano 04); "
                     "janelas em horario local de parede",
    }

    def ativ(aid: str, dur: int, prazo: dict, prio: int = 2, depende: list[str] | None = None) -> dict:
        return {"id": aid, "duracao_min": dur, "prazo": prazo,
                "prioridade": prio, "depende_de": depende or []}

    casos = [
        {**base, "id": "agenda-borda-dev-01", "split": "desenvolvimento",
         "categoria": "prazo-meio-slot",
         "instancia": {
             "janelas": [{"dia": 0, "inicio_min": 540, "fim_min": 720}],
             "limite_diario_min": LIMITE_PADRAO,
             "atividades": [ativ("a1", 60, {"dia": 0, "minuto": 615})]},
         },
        {**base, "id": "agenda-borda-dev-02", "split": "desenvolvimento",
         "categoria": "duracao-nao-multipla-de-slot",
         "instancia": {
             "janelas": [{"dia": 1, "inicio_min": 600, "fim_min": 780}],
             "limite_diario_min": LIMITE_PADRAO,
             "atividades": [ativ("a1", 17, {"dia": 1, "minuto": 780})]},
         },
        {**base, "id": "agenda-borda-val-01", "split": "validacao",
         "categoria": "ciclo-de-dependencias",
         "instancia": {
             "janelas": [{"dia": 2, "inicio_min": 540, "fim_min": 780}],
             "limite_diario_min": LIMITE_PADRAO,
             "atividades": [ativ("a1", 60, {"dia": 2, "minuto": 780}, 2, ["a2"]),
                            ativ("a2", 60, {"dia": 2, "minuto": 780}, 2, ["a1"])]},
         },
        {**base, "id": "agenda-borda-val-02", "split": "validacao",
         "categoria": "incumbent-unknown",
         "instancia": {
             "janelas": [{"dia": 3, "inicio_min": 540, "fim_min": 720}],
             "limite_diario_min": LIMITE_PADRAO,
             "atividades": [ativ("a1", 60, {"dia": 3, "minuto": 720})],
             "incumbent": {"atividade": "a1", "dia": 3, "inicio_min": 540,
                           "status": "UNKNOWN"}},
         },
        {**base, "id": "agenda-borda-test-01", "split": "teste",
         "categoria": "zona-dst",
         "instancia": {
             "janelas": [{"dia": 4, "inicio_min": 540, "fim_min": 780,
                          "transicao_dst": True}],
             "limite_diario_min": LIMITE_PADRAO,
             "atividades": [ativ("a1", 120, {"dia": 4, "minuto": 780})]},
         },
        {**base, "id": "agenda-borda-test-02", "split": "teste",
         "categoria": "prazo-na-borda-demanda-exata",
         "instancia": {
             "janelas": [{"dia": 5, "inicio_min": 540, "fim_min": 780}],
             "limite_diario_min": LIMITE_PADRAO,
             "atividades": [ativ("a1", 240, {"dia": 5, "minuto": 780})]},
         },
    ]

    esperados = {
        "prazo-meio-slot": {
            "esperado": {"viavel": True, "fim_maximo_min": 600,
                         "observacao": "prazo 10:15 nao aproveita o slot 10:00-10:30 "
                                       "(fim 10:30 > 10:15); cabem 60 min nos slots "
                                       "9:00-9:30 e 9:30-10:00"},
            "fundamento": "protocolo secao 4 (F13: prazo meio-slot)",
            "verificacao": "estrutural por construcao da grade de slots"},
        "duracao-nao-multipla-de-slot": {
            "esperado": {"reserva_min": 30, "observacao": "duracao 17 min e "
                         "arredondada para cima para o slot de 30 min (mapa 08 "
                         "secao 12: minutos reservados arredondados)"},
            "fundamento": "protocolo secao 4 (F13: duracao 17 min); mapa 08 secao 12",
            "verificacao": "estrutural por regra citada (nao multipla de 30 min)"},
        "ciclo-de-dependencias": {
            "esperado": {"viavel": False, "diagnostico": "ciclo a1->a2->a1",
                         "observacao": "instancia estruturalmente invalida; "
                                       "rejeicao com diagnostico, nunca plano "
                                       "aprovado"},
            "fundamento": "protocolo secao 4 (F13: ciclo)",
            "verificacao": "estrutural por deteccao de ciclo em grafo de dependencias"},
        "incumbent-unknown": {
            "esperado": {"status": "FEASIBLE", "provas_parciais": True,
                         "observacao": "incumbent UNKNOWN posterior devolve "
                                       "FEASIBLE com provas parciais (mapa 08 "
                                       "secao 12); incumbente invalido nao e "
                                       "promovido"},
            "fundamento": "protocolo secao 4 (F13: UNKNOWN); mapa 08 secao 12",
            "verificacao": "estrutural por regra citada"},
        "zona-dst": {
            "esperado": {"viavel": True,
                         "observacao": "janela marcada com transicao de DST; "
                                       "tratamento em horario local de parede; "
                                       "timezone pendente de confirmacao e "
                                       "registrado como null"},
            "fundamento": "protocolo secao 4 (F13: zona DST)",
            "verificacao": "estrutural; mecanismo executavel pertence a etapa 7"},
        "prazo-na-borda-demanda-exata": {
            "esperado": {"viavel": True, "otimo_por_construcao": True,
                         "makespan_minimo": 780,
                         "observacao": "demanda (240 min) igual a janela (240 "
                                       "min) e prazo no fim da janela: unico "
                                       "cronograma possivel"},
            "fundamento": "protocolo secao 2 (otimo/viabilidade conhecidos)",
            "verificacao": "por forca de construcao (demanda exata)"},
    }
    for caso in casos:
        caso.update(esperados[caso["categoria"]])
    return casos


def main() -> None:
    raiz = Path(__file__).resolve().parents[3]
    destino = raiz / "eval" / "datasets" / "agenda"
    destino.mkdir(parents=True, exist_ok=True)

    pequenas = [gera_pequena(f, i) for f in FAMILIAS for i in range(10)]
    borda = casos_borda()

    # ---- validacoes ----
    assert len(pequenas) == 100, "meta de 100 instancias pequenas"
    assert len(borda) == 6 and all(
        sum(1 for c in borda if c["split"] == s) == n
        for s, n in BORDA_POR_SPLIT.items()), "2 casos de borda por split"

    contagem_split = {"desenvolvimento": 0, "validacao": 0, "teste": 0}
    for inst in pequenas:
        contagem_split[inst["split"]] += 1
        viavel, cronograma = edf_verifica(inst["janelas"], inst["atividades"],
                                          inst["limite_diario_min"])
        assert viavel == inst["esperado"]["viavel"], f"EDF diverge em {inst['id']}"
        assert (cronograma is None) == (inst["esperado"]["cronograma_referencia"] is None)
    assert contagem_split == {"desenvolvimento": 40, "validacao": 20, "teste": 40}, \
        f"proporcao 40/20/40 violada: {contagem_split}"

    for familia, split in FAMILIAS.items():
        splits_da_familia = {i["split"] for i in pequenas if i["familia_parametros"] == familia}
        assert splits_da_familia == {split}, f"familia {familia} repartida entre splits"

    ids = [i["id"] for i in pequenas] + [c["id"] for c in borda]
    assert len(ids) == len(set(ids)), "IDs duplicados"
    conteudos = {json.dumps(i, sort_keys=True, ensure_ascii=False) for i in pequenas}
    assert len(conteudos) == 100, "instancias duplicadas"

    # ---- escrita ----
    for nome, registros in (("pequenas.jsonl", pequenas), ("borda.jsonl", borda)):
        with open(destino / nome, "w", encoding="utf-8") as arq:
            for registro in registros:
                arq.write(json.dumps(registro, ensure_ascii=False) + "\n")

    print(f"OK: {len(pequenas)} pequenas + {len(borda)} borda; split = {contagem_split}")
    for nome in ("pequenas.jsonl", "borda.jsonl"):
        digesto = hashlib.sha256((destino / nome).read_bytes()).hexdigest()
        print(f"sha256({nome}) = {digesto}")


if __name__ == "__main__":
    main()
