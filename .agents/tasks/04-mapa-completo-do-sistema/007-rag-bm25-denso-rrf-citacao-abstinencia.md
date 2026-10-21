# Task 007: RAG — chunking, BM25, denso, RRF, citação e abstinência (mapa §6.4–8, §13.4)

Estado: pendente
Depende de: 006
Origem: nenhuma

## Prompt
Implementar a recuperação (mapa §6 itens 4–8) em `eduagent/services/retrieval.py` e `document.search`: (4) chunking por seção/bloco com alvo 384 tokens e overlap até 64 quando continuidade requerer; IDs e todas as páginas de origem preservados; tabela repete cabeçalhos e referencia células/blocos corretos. (5) BM25 via `rank_bm25.BM25Okapi`, `k1=1.5,b=0.75`, tokenização Unicode lowercase/NFKC sem remover termos técnicos e códigos, versão/hash do tokenizer registrados; busca densa BGE-M3 local com revisão/hash fixados no download, vetor normalizado, produto interno exato; arrays NumPy por snapshot, mapeamento chunk→vetor persistido (ANN/Qdrant é extensão, fora do MVP). (6) Filtrar usuário, disciplina e versão antes do ranking; lexical/denso top-40; RRF `Σ1/(60+rank)` com rank 1-based, empate pelo ID. Reranker `BAAI/bge-reranker-v2-m3` é opcional: configurar inicialmente SEM reranker se co-residência inviável e registrar a seleção em validação como pendência — não decidir agora. (7) `EvidencePack` até 4.096 tokens; fonte `[doc_id@version:página:bloco]` resolve ao original armazenado; validator confere IDs, offsets e versão; apoio semântico avaliado separadamente. (8) Sem resposta documental, declarar ausência de evidência (`NO_EVIDENCE`/coverage `none`); explicação geral rotulada e sem citação fictícia; limiar de abstinência ajustado em validação (não sigmoid como probabilidade). Índice publicado só após construção completa.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §6.4–8; §13.4; tabela `document.search` (§10).
- Ingestão (006) com blocos/chunks; contratos (003).

## Corretude
- [ ] C1 — Chunking 384/64 com IDs e páginas preservados; tabelas com cabeçalhos repetidos e referência correta.
- [ ] C2 — BM25 e denso conforme parâmetros do mapa; hashes registrados; RRF com fórmula/rank 1-based/desempate por ID, verificado em teste unitário com caso conhecido.
- [ ] C3 — Filtros de usuário/disciplina/versão antes do ranking (teste prova isolamento entre usuários); citação `[doc_id@version:página:bloco]` resolve ao original; `EvidencePack` respeita 4.096 tokens.
- [ ] C4 — Sem reranker na configuração inicial e pendência de validação registrada; abstinência sem citação fictícia; mapa intocado; commits separados.

## Notas

### Dificuldade esperada
5/10 — Índices duplos + RRF com determinismo; download do BGE-M3 pinado; risco de vazamento entre usuários nos filtros.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
