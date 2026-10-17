# Plano: Implementação do EduAgent-OS v0.1 (núcleo textual local)

Estado: rascunho

## Objetivo

Implementar o núcleo textual local do EduAgent-OS v0.1 conforme a especificação
implementável do mapa (mapa §1): cinco agentes lógicos (Curador, Bibliotecário,
Tutor, Monitor, Planejador) em LangGraph, com ingestão PDF/texto, RAG com
citações resolvíveis, tutoria/quiz/flashcards/autoexplicação, evidências
formativas, memória temporal e agenda semanal com exportação ICS. Web e
sincronização de calendário são módulos opcionais com contrato definido; sua
ausência não bloqueia o núcleo. Este plano cobre especificação, não aplicação
executável pronta: o mapa de testes (etapa 8) é quem define critérios
quantitativos e dados de teste.

## Abordagem

Ordem de construção em alto nível conforme mapa §13, cada etapa com gate de
aceite próprio antes da seguinte:

1. Manifesto/hardware e gate de modelo: carregar o candidato Bonsai 2 offline
   (mapa §3.1), validar tokenizer/JSON/tools negadas; se falhar, marcar
   `MODEL_NOT_ADMITTED` sem substituição silenciosa.
2. Contratos Pydantic estritos, DDL/migrações SQLite e commit idempotente
   (mapa §4–5, §11); validar crash/replay.
3. Ingestão (Docling + OCR seletivo), proveniência e confirmação de fatos
   pelo usuário (mapa §6).
4. RAG lexical (BM25) + denso (BGE-M3) + RRF, citação resolvível e abstinência
   documental (mapa §6); reranker decidido em validação.
5. Skills YAML, estados do Tutor, Monitor com rubrica por critério e redutor
   determinístico observado (mapa §8, §15.2).
6. Memória temporal, montagem de contexto com checagem de síntese, correção e
   deleção com propagação (mapa §7, §5).
7. Solver CP-SAT com objetivo lexicográfico + verificador independente
   separado, preview/confirmação e ICS RFC5545 (mapa §9, §15.5).
8. Grafo completo com intenções/rotas, checkpoints, pausas, limites e traces
   (mapa §10, §12); ensaio longitudinal offline.
9. Conectores opcionais (web, sync de calendário) admitidos individualmente
   após contratos e falhas de rede (mapa §6, §9).
10. Congelar manifesto e emitir relatório de testes conforme etapa 8 (mapa
    §13.10).

Invariantes transversais que condicionam tudo: snapshot/ownership com
`domain_revision` monotônica (mapa §15.1), commit idempotente com recibo
(mapa §11), erros tipados com retryability (mapa §4), e nenhuma saída parcial
silenciosamente aprovada (mapa §12).

## Escopo

- MVP: cinco agentes, ingestão, RAG, tutoria/avaliação, memória, agenda/ICS,
  CLI mínima e API loopback (mapa §12, §1).
- Fora do MVP: notas oficiais, treinamento fundacional, voz, vídeos gerados,
  sistemas acadêmicos fechados, multiusuário concorrente em rede (segurança de
  dados por usuário existe desde o esquema), BKT (só shadow mode futuro),
  ANN/Qdrant (extensão), A2A distribuído (adiado) (mapa §1, §8, §14, §15.6).
- Módulos opcionais com contrato: curadoria web, sync via MCP/CalDAV/Google
  (mapa §6, §9). Sem credenciais/conector, não bloqueiam o núcleo.
- Defaults numéricos (janelas de contexto, budgets, limites de ingestão,
  parâmetros BM25/RRF/solver) são defaults de ensaio a calibrar no hardware
  registrado antes do congelamento — não resultados medidos (mapa §1, §3).

## Contexto

- `fase2/documentos/04_mapa_completo_do_sistema.md` — fonte normativa única e
  autocontida; o executor deve lê-lo integralmente e tratar "deve" como
  contrato. As seções §15 fecham decisões da auditoria e prevalecem quando
  especificam regra mais precisa.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — critérios quantitativos,
  dados e aceites de teste (referenciado, fora do escopo deste plano).
- `fase2/documentos/11_indice_da_entrega.md` — índice dos entregáveis.
- `fase2/pesquisa/` — fundamentos e registro histórico (pesquisas 3/7); não
  normativo.

## Critérios de conclusão

Aceite funcional do mapa §13.235, verificável por inspeção/execução:

- Cada rota do grafo (mapa §10) termina com estado definido; cancelamento e
  deadline produzem terminais com erro tipado e artefatos já válidos.
- Cada artefato cumpre o contrato Pydantic da tabela do mapa §4 (inclusive
  invariantes de `*_ref`, spans e confirmações).
- Toda citação `[doc_id@version:página:bloco]` resolve ao original armazenado.
- Toda escrita passa pelo commit idempotente com recibo e versionamento
  (`expected_version`/`domain_revision`); crash/replay não duplica nem perde
  efeito reconhecido.
- Nenhum plano sem validação do verificador independente é publicado como
  aprovado; nenhum ICS é gerado sem plano confirmado.
- Uma sessão retomada de checkpoint preserva item pendente, nível de ajuda e
  histórico do turno.
- Uso de evidências: zero evidência → `insufficient`; sequência `favorable`
  exige três tentativas independentes/aceitas/decidíveis de famílias distintas,
  todas corretas e posteriores ao último erro crítico aceito
  (mapa §8, §15.2) — regra aplicada exatamente como especificada.
- Ingestão acima dos limites é recusada ou dividida; versão incompleta nunca
  vira ativa (mapa §3, §12).
- Manifesto congelado com versões reais (pacotes, modelo, tokenizer, skills)
  em `manifest.json` e `uv.lock`; `MODEL_NOT_ADMITTED` bloqueia tutoria.
- Relatório de testes emitido conforme etapa 8, sem preencher ausência de
  resultados experimentais com estimativas inventadas (mapa §13.235).

## Questões abertas

- Reranker (`BAAI/bge-reranker-v2-m3`): decisão de adotar ou não depende de
  co-residência e validação; o mapa define seleção em validação (mapa §6.6).
- Conector de busca web: deve ser escolhido/configurado na implementação;
  sem ele, `CONNECTOR_DISABLED` (mapa §6).
- Modo do modelo (non-thinking vs thinking): mapa §3.1 manda testar
  non-thinking primeiro e comparar thinking em desenvolvimento; perfil final é
  congelado no manifesto — decisão pendente de validação.
- Timezone default `America/Sao_Paulo` requer confirmação antes de fixar
  (mapa §3).
- Suporte a JSON schema no fork do runtime (`prism-b10743-adfffbe`): capacidade
  a verificar e fixar por hash; parse/schema/política permanecem obrigatórios
  independentemente (mapa §3.1).

## Tasks

<A preencher pelo task-writer.>
