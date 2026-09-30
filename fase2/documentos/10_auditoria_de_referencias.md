# 10 — Auditoria de referências da metodologia

**Data:** 30/09/2026. **Arquivos produzidos:** `fase2/references.bib` e este relatório.

**Nota de revisão:** números de linha na tabela identificam a versão auditada antes do fechamento operacional e dos ajustes tipográficos; os contextos e chaves permanecem os mesmos na versão final. Mapas4/8 são normativos. Uma checagem mecânica posterior e compilação BibTeX/LaTeX verificaram novamente as44chaves sem ausências; não foram introduzidas novas citações.

## 1. Resultado e procedimento

Foram lidos integralmente `fase2/fase2_metodologia.tex`, os quatro `fase2/pesquisa/references_*.bib` e os quatro relatórios de pesquisa, incluindo suas tabelas de fontes, tentativas e limitações. Cada chave citada foi confrontada com a entrada bibliográfica e com o registro verificável de consulta da pesquisa correspondente: autoria, título, ano, DOI quando registrado, URL, versão e alcance do trecho que a cita.

Esta auditoria confere os registros de pesquisa e sua utilização no texto; **não representa nova leitura remota de todos os artigos**. Os acessos remotos anteriores são os documentados nas pesquisas de 30/09/2026. Como conferência adicional pontual, o [prefácio primário de Lakens](https://lakens.github.io/statistical_inferences/) foi novamente recuperado nesta auditoria: confirma autor, título, citação recomendada com ano 2022 e DOI `10.5281/zenodo.6409077`, descrevendo a obra como recurso educacional aberto e livro atualizado regularmente.

| Inventário | Entradas de origem | Fontes únicas acrescentadas |
|---|---:|---:|
| `references_arquitetura.bib` | 18 | 18 |
| `references_pedagogia.bib` | 18 | 18 |
| `references_avaliacao_qualidade.bib` | 8 | 8 |
| `references_robustez.bib` | 13 | 12, descontando Zheng |
| **Total** | **57** | **56** |

- **44 chaves distintas citadas**, todas presentes uma única vez na bibliografia consolidada; **zero chaves ausentes**.
- **12 fontes não citadas** também preservadas, pois a consolidação abrange todas as fontes únicas dos quatro arquivos.
- **15 documentos sem data editorial verificada**, dos quais **11 citados**, receberam `year = {s.d.}` e `note = {Acesso em 30/09/2026}` (eventualmente acompanhado de versão curta).
- **Uma duplicata resolvida** (`zheng2023judge`) e **uma inadequação estrutural BibTeX corrigida** (`lakens2022inferences`, detalhada na seção 4).
- **Zero divergências novas de identidade bibliográfica** (autor/título/ano/DOI/URL) detectadas no confronto com as pesquisas. Limitações de leitura não são erros de identidade nem evidência de leitura integral.

As 12 fontes não citadas são: `llamasrv`, `ytcaptions`, `uvlock`, `wood1976tutoring`, `farquhar2024semanticentropy`, `corbett1995knowledgetracing`, `googleEmployeeScheduling`, `google2026calendarcreate`, `sqliteTesting`, `athalye2017porcupine`, `sklearnKappaQuality` e `sklearnCalibrationQuality`.

## 2. Deduplicação, datas, versões e apresentação

### Deduplicação

`zheng2023judge` identifica a mesma obra, ano 2023 e arXiv `2306.05685`, nos arquivos de qualidade e robustez. Foi mantida **a entrada de `references_avaliacao_qualidade.bib`**, com os 13 autores, DOI arXiv, `primaryClass = {cs.CL}` e URL do registro v4. A entrada de robustez também continha os 13 autores, mas não DOI nem classe primária. Seu registro de leitura em HTML complementa o alcance da consulta, sem gerar segunda obra ou chave. A nota consolidada limita-se à versão v4 de 24/12/2023.

Não foram criadas entradas adicionais para páginas auxiliares, API do Hub, HTML do mesmo artigo, código BEIR ou documentação reconsultada. Os respectivos links e logs continuam em `pesquisa/` e, quando necessários para compreender a citação, na tabela abaixo.

### Datas e versões

- `s.d.` significa **ausência de data editorial verificada no conteúdo inspecionado**, não publicação em 2026. O valor textual no campo `year` atende ao uso autor–ano de `plainnat`; `urldate` registra o acesso em formato ISO e `note` torna a data de acesso visível mesmo em estilos que ignoram `urldate`.
- As 15 chaves com `s.d.` são `llamasrv`, `docling`, `ocrpdf`, `bgerank`, `qdranthyb`, `lgstate`, `lginterrupt`, `pydstrict`, `oteltrace`, `googleEmployeeScheduling`, `jiwerQuality`, `sklearnKappaQuality`, `sklearnCalibrationQuality`, `hypothesisStateful` e `scipyBootstrap`. **Não foram convertidas em publicações de 2026.**
- Anos de documentação com data explícita foram preservados como atualização/estado documentado: CP-SAT 2024; SQLite WAL 2026 (25/08); SQLite Testing 2026 (21/04); YouTube Captions 2026 (15/09); uv 2026 (05/08); Google Calendar Create events 2026 (11/09); Bonsai/model card/demo 2026. Isso não data a origem das técnicas ou do software.
- MCP conserva **2025**, ano da especificação identificada `2025-11-25`, não o acesso em 2026. BFCL conserva 2024, release V3/atualização documentadas; Porcupine conserva 2017 conforme citação fornecida pelo README.
- MemGPT: ano do preprint original **2023**, revisão v2/2024 em nota. M3: preprint **2024**, revisão v5/2025 em nota. MetaGPT: entrada da revisão arXiv v7/**2024**, primeiro preprint 2023, sem inventar conferência verificada. LongMemEval: ICLR **2025**, primeiro preprint 2024. AgentBench: ICLR **2024**, leitura na revisão v3/2025. RAGAs: publicação EACL **2024**, leitura metodológica na revisão arXiv v2/2025. Essas diferenças foram mantidas explicitamente.
- Corbett conserva **1995**, conforme registro editorial/Crossref da pesquisa, embora pyBKT cite 1994; não é nova inconsistência criada pela consolidação. Chen conserva publicação online **2018**, com fascículo impresso em 2019 indicado em nota. Chi conserva publicação original **1994**, não disponibilização online posterior.

### Notas e escaping

Notas extensas de auditoria, bloqueios HTTP, publicação não conferida, execução ausente e tentativas descartadas foram retiradas da bibliografia de apresentação. Foram mantidas notas curtas essenciais de versão/revisão, atualização editorial, editor da RFC e acesso de documentação. O alcance da leitura continua verificável nos relatórios de pesquisa.

Todas as URLs do consolidado estão em **`url`**, com underscores literais, por exemplo `docling_document`, `strict_mode`, `security_best_practices` e `statistical_inferences`. Não há URLs cruas em `note` nem `\_` dentro de URLs. No título textual `cohen\_kappa\_score`, o escape é apropriado por se tratar de texto TeX; underscores em identificadores de DOI permanecem no campo `doi`. O título original de BEIR, **“Heterogenous”**, foi conservado conforme a pesquisa, sem corrigir editorialmente a grafia do trabalho.

## 3. Auditoria individual de todas as chaves citadas

**Registros locais usados na coluna Pesquisa:**

- **A:** [`03a_arquitetura_rag.md`](../pesquisa/03a_arquitetura_rag.md), §5 (fontes), com contexto nos requisitos C01–C20.
- **P:** [`03b_pedagogia_memoria_planejamento.md`](../pesquisa/03b_pedagogia_memoria_planejamento.md), §10 (fontes), com contextos nas §§3–9.
- **Q:** [`07a_metodos_qualidade.md`](../pesquisa/07a_metodos_qualidade.md), §11 (fontes), com contextos O01–O18.
- **R:** [`07b_metodos_robustez_experimentos.md`](../pesquisa/07b_metodos_robustez_experimentos.md), §10.2 (fontes), com contextos M01–M08 e §8.

**Correto:** identidade e atribuição compatíveis com conteúdo registrado como lido. **Limitado:** identidade correta, mas fundamentação disponível apenas por metadados, resumo ou leitura restrita que exige ressalva. Nenhuma das duas classificações afirma eficácia do EduAgent-OS, reprodução de benchmarks ou conformidade de implementação. Linhas referem-se ao `.tex` auditado.

| Nº | Chave / linha(s) | Pesquisa e fonte primária / registro verificável | Alcance de acesso e contexto da citação | Parecer |
|---:|---|---|---|---|
| 1 | `hong2024metagpt` — 72 | P §10, item 7; [arXiv v7](https://arxiv.org/html/2308.00352v7), Hong et al., 2024 | §§3–4, SOPs, papéis e artefatos em engenharia de software; lista de 15 autores conforme texto. OpenReview bloqueado; entrada é arXiv, não conferência inferida. | **Correto**, adaptação arquitetural, sem evidência educacional. |
| 2 | `sun2025multitutor` — 72 | P §10, item 4; [PMLR 273](https://proceedings.mlr.press/v273/sun25a.html), Sun e Tai, 2025 | Página/BibTeX e PDF §§2–3 lidos; papéis/estado estruturado; 25 perguntas simuladas com juiz GPT-4o, não alunos reais. | **Correto**, inspiração para especialização, não ganho causal. |
| 3 | `packer2023memgpt` — 72 | P §10, item 5; [registro v2](https://arxiv.org/abs/2310.08560v2) e [HTML](https://arxiv.org/html/2310.08560v2), Packer et al., 2023/v2 2024 | §§2–3, contexto ativo/externo, ferramentas, FIFO, resumo e recall; nenhuma garantia de memória pedagógica/transações. | **Correto**, ano original e revisão separados. |
| 4 | `wang2023voyager` — 72 | P §10, item 6; [arXiv v2](https://arxiv.org/abs/2305.16291v2), Wang et al., 2023 | HTML §§2–4, biblioteca de programas, recuperação e feedback em Minecraft. Skills pedagógicas são adaptação. | **Correto**, sem transportar eficácia ou compressão sem perdas. |
| 5 | `gou2024tora` — 72 | P §10, item 8; [arXiv v4](https://arxiv.org/abs/2309.17452v4), Gou et al., ICLR 2024 | Registro confirma venue; HTML §§2–3, ferramentas e treinamento matemático. CP-SAT/solver de agenda são projeto próprio. | **Correto**, analogia delimitada. |
| 6 | `docling` — 126 | A §5; [Docling document](https://docling-project.github.io/docling/concepts/docling_document/), Docling Project, s.d. | Documentação da representação, ordem, tabelas e proveniência. URL antiga `concepts/document/` retornou 404 e foi descartada. | **Correto**, documentação não prova fidelidade de OCR. |
| 7 | `ocrpdf` — 126 | A §5; [Cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html), OCRmyPDF contributors, s.d. | Idiomas, sidecar e processamento; sidecar omite páginas já textuais/não OCRizadas. Página latest com funcionalidades v17. | **Correto**, motivação de reextração completa; limites numéricos são locais. |
| 8 | `bonsai2` — 157 | A §5/C01; [model card](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/README.md) e [API com blobs](https://huggingface.co/api/models/prism-ml/Ternary-Bonsai-2-27B-gguf?blobs=true), Prism ML, 2026 | Card/API identificam revisão `b072e1d3b35a0a630cece372c2127528e0994386` e SHA-256 LFS `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` de PTQ1_0. Hash publicado, não recalculado; licença/NOTICE e execução pendentes. | **Correto**, texto exige admissão e recálculo, sem alegar benchmark local. |
| 9 | `bonsaidemo` — 159 | A §5/C01; [README oficial](https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/README.md), Prism ML, 2026 | Estado 25/09/2026; fork obrigatório e release `prism-b10743-adfffbe`. Setup/binários não executados. | **Correto**, runtime candidato; não pressupõe paridade com upstream. |
| 10 | `m3` — 184 | A §5/C04; [arXiv 2402.03216](https://arxiv.org/abs/2402.03216), Chen et al., 2024/v5 2025 | Metadados e abstract: modalidades, idiomas e comprimento. Texto integral e desempenho específico em português não lidos. | **Limitado**, seleção de candidato sustentada pelo resumo; parâmetros BM25 são locais. |
| 11 | `rrf09` — 188 | A §5/C04; [Crossref DOI](https://api.crossref.org/works/10.1145/1571941.1572114), Cormack, Clarke e Buettcher, SIGIR 2009 | **Metadados-only**: autores/título/venue/páginas/DOI. PDF primário retornou bytes ilegíveis/truncados. Fórmula, resultados e `k=60` não foram verificados no artigo. | **Limitado**, limitação expressa na linha 188; operacionalização vem de Qdrant e escolha local. |
| 12 | `qdranthyb` — 188 | A §5/C04; [Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/concepts/hybrid-queries/), Qdrant, s.d. | Trechos legíveis sobre RRF/DBSF/prefetch; retorno truncado; conteúdo aponta rota canônica `search/hybrid-queries/`. Defaults/ranks do produto diferem da fórmula local. | **Correto**, apoio operacional, não confirmação histórica de `k=60`. |
| 13 | `bgerank` — 188 | A §5/C04; [model card BAAI](https://huggingface.co/BAAI/bge-reranker-v2-m3/raw/main/README.md), BAAI, s.d. | Multilingual, pares query/passagem, scores e exemplo truncado em 512 tokens; gráficos não analisados quantitativamente. | **Correto**, reranker opcional e ganho condicionado à validação. |
| 14 | `roediger2006testing` — 194 | P §10, item 3; [PDF no laboratório do coautor](https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf), Roediger III e Karpicke, 2006; DOI `10.1111/j.1467-9280.2006.01693.x` | Metadados/resumo e PDF convertido/lido: introdução/método/avaliação do experimento 1, recuperação versus releitura e retenção tardia. | **Correto**, motiva recuperação; intervalos 1/3/7 e feedback automático não são resultado da fonte. |
| 15 | `chi1994selfexplanation` — 194 | P §10, item 2; [DOI original](https://doi.org/10.1207/s15516709cog1803_3) e [Crossref](https://api.crossref.org/works/10.1207/s15516709cog1803_3), Chi et al., 1994 | Metadados e resumo experimental depositado pelo editor, não integral; autoexplicação em circulação humana com alunos da oitava série. | **Limitado**, motivação compatível com resumo; sem transportar efeito para graduação/local. |
| 16 | `wu2025longmemeval` — 200 | P §10, item 13; Q §11, item 7; [arXiv v2](https://arxiv.org/abs/2410.10813v2), Wu et al., ICLR 2025 | HTML §§3–5/trechos reconsultados: extração, multissessão, temporalidade, atualização e abstenção; apêndice de meta-avaliação não auditado. | **Correto**, adapta categorias; não garante exclusão transacional ou ouro português. |
| 17 | `badrinath2021pybkt` — 213 | P §10, item 12; [arXiv v2](https://arxiv.org/abs/2105.00385v2), Badrinath, Wang e Pardos, 2021 | Texto com equações, EM, extensões e suficiência sintética; aceitação EDM indicada no registro, entrada permanece arXiv. | **Correto**, extensão futura ajustada/calibrada, não inferência já válida. |
| 18 | `google2024cpsat` — 226 | P §10, item 14; Q §11, item 11; [CP-SAT Solver](https://developers.google.com/optimization/cp/cp_solver), Google, atualização 28/08/2024 | Documentação primária de inteiros e cinco status. Formulação educacional e interpretação de demandas não são prescritas pela API. | **Correto**, fronteira solver/interpretação explícita. |
| 19 | `lgstate` — 237 | A §5/C13; [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) e [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), LangChain, s.d. | Threads, super-steps, pending writes, checkpoint versus store e modos de durabilidade; URL antiga durable-execution devolveu Persistence. | **Correto**, checkpoint separado do commit de domínio. |
| 20 | `lginterrupt` — 237 | A §5/C13; [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), LangChain, s.d. | Pause/resume com checkpointer e reinício do nó desde o começo; exemplos de traces vinculados não abertos. | **Correto**, preparação pura e efeitos idempotentes na linha 243. |
| 21 | `pydstrict` — 241 | A §5/C14; [Strict Mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), Pydantic contributors, s.d. | Coerção/modo estrito e exceções de datas em JSON. Campos extras, ownership e validação de efeito são contratos adicionais do projeto. | **Correto**, validação estrutural não apresentada como autorização. |
| 22 | `mcparch` — 247 | A §5/C14; [Architecture 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/architecture), MCP contributors, 2025 | Host/client/server, JSON-RPC e negociação de capacidades, não sandbox/transações nem comunicação pedagógica. | **Correto**, possível padronização de fronteiras externas. |
| 23 | `mcpsec` — 270 | A §5/C15; [Security Best Practices 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices), MCP contributors, 2025 | SSRF/redirects, permissões locais, sessão/token/scopes. Fetch e isolamento locais são adaptações a testar. | **Correto**, efetividade não presumida. |
| 24 | `sqlitewal` — 282 | A §5/C16; Q §11, item 13; R §10.2, item 10; [WAL](https://sqlite.org/wal.html), SQLite developers, atualização 25/08/2026 | Concorrência, FULL/NORMAL, WAL/cópia e correção WAL-reset em 3.51.3 ou backports corrigidos. Outbox/idempotência entre bancos não decorrem de WAL. | **Correto**, protocolo local descrito separadamente nas linhas 284–286. |
| 25 | `desruisseaux2009icalendar` — 292 | P §10, item 16; Q §11, item 12; R §10.2, item 9; [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545.html), Desruisseaux (editor), 2009 | Consulta direcionada §§3.1, 3.6.1 e 3.8.7.2–4: UTF-8/CRLF/folding, fim exclusivo/DATE, UID e revisão. Não leitura integral de 175 páginas. | **Correto**, sem METHOD, DTSTAMP por última revisão e retries estáveis; UID sem garantia universal. |
| 26 | `daboo2007caldav` — 294 | P §10, item 17; [RFC 4791](https://www.rfc-editor.org/rfc/rfc4791.html), Daboo, Desruisseaux e Dusseault, 2007 | Recursos, UID único, PUT/ETags/precondições §§4.1, 5.3.2–5.3.4 e consulta por UID. Não prova contrato de outros backends. | **Correto**, If-None-Match/If-Match limitados a CalDAV. |
| 27 | `oteltrace` — 296 | A §5/C17; Q §11, item 14; R §10.2, item 8; [Traces](https://opentelemetry.io/docs/concepts/signals/traces/), OpenTelemetry Authors, s.d. | Spans, contexto/IDs, attributes/events/links/status/exporters; JSON ilustrativo não OTLP. Não instrumenta tokens/VRAM/energia automaticamente. | **Correto**, contadores e amostragem propostos explicitamente. |
| 28 | `thakur2021beir` — 318 | Q §11, item 2; [arXiv](https://arxiv.org/abs/2104.08663) e [código oficial](https://raw.githubusercontent.com/beir-cellar/beir/main/beir/retrieval/evaluation.py), Thakur et al., 2021 | Artigo: metadados/abstract v4, não integral. Código EvaluateRetrieval lido: pytrec_eval, cortes, remoção de IDs e médias; main móvel, não executado. | **Limitado**, apoio metodológico de ranking também vem do código; sem importar resultados. |
| 29 | `gao2023alce` — 318 | Q §11, item 3; [ACL EMNLP](https://aclanthology.org/2023.emnlp-main.398/) e [arXiv HTML](https://arxiv.org/html/2305.14627), Gao et al., 2023 | Metadados ACL; HTML v2 §§2–3, corretude, recall/precision e apoio conjunto; avaliação humana/apêndices não integralmente lidos. | **Correto**, claims atômicas são adaptação da unidade predominantemente sentencial. |
| 30 | `es2024ragas` — 318 | Q §11, item 4; [ACL EACL](https://aclanthology.org/2024.eacl-demo.16/) e [arXiv HTML](https://arxiv.org/html/2309.15217), Es et al., 2024/revisão 2025 | Metadados de publicação; revisão v2 §§3–5, fidelidade/relevâncias/WikiEval/limites. API atual não auditada. | **Correto**, ano editorial e revisão separados; escore não é prova de correção. |
| 31 | `jiwerQuality` — 328 | Q §11, item 1; [JiWER](https://jitsi.github.io/jiwer/) e [Usage](https://jitsi.github.io/jiwer/usage/), Jitsi/JiWER contributors, s.d. | CER/WER, alinhamentos/transformações/API e referências vazias desde 4.0; transferência ASR→OCR, pacote não executado. | **Correto**, taxas podem exceder 1; transcrição humana é referência. |
| 32 | `kim2024prometheus` — 349 | P §10, item 9; Q §11, item 6; [arXiv v2](https://arxiv.org/abs/2310.08491v2), Kim et al., ICLR 2024 | Entradas/rubricas/referência, construção e avaliação humana; reconsulta §§3–5, truncada nos resultados/apêndices. Modelo treinado para respostas de LLM, não estudantes portugueses. | **Correto**, motivação de rubricagem, sem supor capacidade do Bonsai. |
| 33 | `guo2017calibration` — 351 | Q §11, item 8; [PMLR 70](https://proceedings.mlr.press/v70/guo17a.html) e [arXiv HTML](https://arxiv.org/html/1706.04599), Guo et al., 2017 | Identidade editorial; HTML v2 §§2/4, confiabilidade/ECE/NLL/calibradores. Título renderizado de suplementos também contém texto principal; nem todos gráficos/suplementos lidos. | **Correto**, motivação de calibração prospectiva. Brier binário também é operacionalizado em Q §7 e no guia scikit-learn, não atribuição exclusiva a Guo. |
| 34 | `debenedetti2024agentdojo` — 382 | R §10.2, item 7; [arXiv v3](https://arxiv.org/html/2406.13352v3), Debenedetti et al., 2024 | Metadados e §§1–4 legíveis: utilidade, segurança, estado e objetivos de ataque; retorno truncado e código não executado. | **Correto**, adaptação de objetivos legítimo/adversarial, sem alegar defesa reproduzida. |
| 35 | `liu2024agentbench` — 382 | R §10.2, item 6; [arXiv v3](https://arxiv.org/html/2308.03688v3) e [registro](https://arxiv.org/abs/2308.03688), Liu et al., ICLR 2024 | §§2–4, ambientes/trajetórias/términos; autores conforme HTML; revisão v3 de 2025, apêndices incompletos. | **Correto**, venue 2024 distinto da revisão consultada 2025. |
| 36 | `bfclMultiTurn` — 382 | R §10.2, item 5; [BFCL V3](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html) e [blog inicial](https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html), Mao et al., 2024 | Documentação de curadoria, AST/execução, multi-turn/multi-step, estado e resposta. V4 não consultado; entrada não é artigo BFCL. | **Correto**, diálogo com fluxos, não transferência de escore do leaderboard. |
| 37 | `hypothesisStateful` — 388 | R §10.2, item 2; [Stateful tests](https://hypothesis.readthedocs.io/en/latest/stateful.html), Hypothesis contributors, s.d. | Regras/Bundles/precondições/invariantes, referência simplificada e redução de sequências; página latest móvel. | **Correto**, sequências/invariantes locais propostos. |
| 38 | `chen2018metamorphic` — 388 | R §10.2, item 1; [Crossref DOI](https://api.crossref.org/works/10.1145/3143561), Chen et al., online 2018/impresso 2019 | Metadados e resumo editorial, integral ACM bloqueado; definição de metamorfismo, não validação das relações locais. | **Limitado**, relações derivadas dos contratos; parâmetros e casos não extraídos do artigo. |
| 39 | `zheng2023judge` — 394 | Q §11, item 5; R §10.2, item 15; [registro v4](https://arxiv.org/abs/2306.05685v4) e [HTML v4](https://arxiv.org/html/2306.05685v4), Zheng et al., 2023 | Q §§3–4 e R §§1–6 legíveis; posição/verbosidade/referência/empates e limites de raciocínio, apêndices truncados. DOI/autores da entrada Q preferida. | **Correto**, ordem dupla e meta-avaliação; acordo de preferências não valida julgamento formativo. |
| 40 | `dror2018hitchhiker` — 396 | R §10.2, item 11; [ACL P18-1128](https://aclanthology.org/P18-1128/), Dror et al., 2018 | Resumo e metadados, PDF não lido; adequação da análise ao desenho/métrica. | **Limitado**, sem atribuir receita de bootstrap ou correção Holm detalhada ao texto não lido. |
| 41 | `field2007cluster` — 398 | R §10.2, item 12; [Crossref DOI](https://api.crossref.org/works/10.1111/j.1467-9868.2007.00593.x), Field e Welsh, 2007 | Resumo editorial/metadados via DOI/Crossref; integral Oxford bloqueado. Validade depende dos modelos estudados. | **Limitado**, motiva preservar dependência; não garante IC com poucos clusters ou dependência cruzada. |
| 42 | `scipyBootstrap` — 398 | R §10.2, item 13; [scipy.stats.bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), SciPy community, s.d. | Documentação exibida 1.18.0: paired/índices, métodos, RNG e degeneração. paired=True não cria agrupamento. | **Correto**, implementação explícita por cluster e validação de cobertura ainda propostas. |
| 43 | `lakens2022inferences` — 402 | R §10.2, item 14; [livro/prefácio](https://lakens.github.io/statistical_inferences/) e [capítulo 8](https://lakens.github.io/statistical_inferences/08-samplesizejustification.html), Lakens, 2022 | Prefácio/citação e §§8.1–8.8 legíveis, capítulo truncado; potência/precisão/recursos. Artigo Collabra bloqueado não é a obra citada. | **Correto**, livro efetivamente consultado; representação BibTeX corrigida na seção 4. |
| 44 | `pineau2021reproducibility` — 406 | R §10.2, item 16; [JMLR 22(164)](https://jmlr.org/papers/v22/20-303.html), Pineau et al., 2021 | Resumo/metadados, PDF não lido; transparência/reprodução. Inventário e ensaio offline são decisões locais. | **Limitado**, fundamentação geral, sem afirmar receita detalhada ou reprodução do artigo. |

**Síntese do alcance:** são **8 chaves limitadas e 36 corretas**: a lista de oito é `m3`, `rrf09`, `chi1994selfexplanation`, `thakur2021beir`, `chen2018metamorphic`, `dror2018hitchhiker`, `field2007cluster` e `pineau2021reproducibility`. Leitura direcionada/truncada está anotada também em referências corretas; a classificação considera se o alcance efetivamente cobre a atribuição feita no `.tex`.

## 4. Correção e trechos relevantes do relatório

### Inadequação estrutural corrigida: Lakens

Na origem, `lakens2022inferences` era `@book` sem `publisher`, campo exigido por `plainnat` para esse tipo. A pesquisa identifica um livro online e a citação recomendada não fornece editora. A conferência pontual do prefácio confirmou autor/2022/DOI e essa forma de disponibilização.

O consolidado usa **`@misc` com `howpublished = {Livro online, recurso educacional aberto}`**, conserva autor, título, ano, DOI e URL do capítulo efetivamente lido, e acrescenta nota curta de capítulo/acesso. Não foi fabricada editora nem substituída a obra pelo artigo Collabra bloqueado. Trata-se de correção de representação bibliográfica para o estilo, não divergência na identidade da obra.

**Trecho relacionado:** `fase2_metodologia.tex`, linha 402, “Piloto apenas em desenvolvimento simulará diferenças pareadas por cluster [...] estimando potência e precisão [...]”. O capítulo lido sustenta planejamento/justificativa de amostra, mas a simulação hierárquica específica é proposta local; o trecho é compatível com a pesquisa e não precisou de alteração.

### Limitações expressamente conferidas

- **Linha 188 — RRF:** “A referência de RRF foi conferida por metadados”. Isso corresponde ao acesso **metadados-only** registrado em A. O `60` da equação é escolha local documentada em A/C04, não parâmetro histórico confirmado pelo PDF. O complemento Qdrant é documentação operacional, não leitura retroativa do artigo.
- **Linha 194 — pedagogia:** “sem transportar seus efeitos automaticamente para este protótipo”. Corresponde aos limites de Chi (resumo editorial) e Roediger (experimento lido); os intervalos 1/3/7 são política local.
- **Linha 292 — RFC/DTSTAMP:** a exportação está explicitamente **sem METHOD**, com DTSTAMP/LAST-MODIFIED na última revisão persistida e CREATED na criação. Isso já resolve a divergência dos documentos anteriores apontada em Q/O14, conforme RFC 5545 §3.8.7.2. Não foi identificada inconsistência nesse trecho da metodologia.
- **Linhas 318, 351, 396, 398 e 406 — avaliação:** a adaptação de BEIR, calibração, adequação de inferência, bootstrap e reprodução é compatível com as pesquisas; artigo BEIR integral, PDFs de Dror/Field/Pineau e provas de validade dos ICs não foram lidos/reproduzidos. Fórmulas locais de Brier e kappa também constam da documentação scikit-learn consultada em Q, preservada entre as 12 entradas não citadas. Não se considera a citação contextual de Guo/Prometheus prova exclusiva da origem dessas fórmulas.

**Metadados-only adicionais não citados:** Wood e Corbett foram preservados na bibliografia completa, mas as pesquisas só verificaram sua identidade. A remoção das notas extensas não promove esses registros a leitura integral. RRF é o único citado com acesso estritamente metadados-only; M3/Chi/Chen/Dror/Field/Pineau incluem resumo/abstract, e BEIR ainda inclui código oficial lido.

## 5. Padrão de citações e carregamento da bibliografia

O `.tex` carrega `natbib` com `[authoryear,round]` (linha 6) e define:

```tex
\let\cite\citep
\let\citeonline\citet
```

Assim, **`\cite{chave}` é citação parentética autor–ano**; **`\citeonline{chave}` é citação narrativa**. O texto auditado usa `\cite` para as 44 chaves; não há chamada efetiva de `\citeonline`, somente sua definição. Listas de chaves separadas por vírgula seguem o padrão natbib; as keys foram preservadas exatamente, inclusive maiúsculas em `jiwerQuality`, `bfclMultiTurn`, `hypothesisStateful` e `scipyBootstrap`.

No final, linhas 516–517:

```tex
\IfFileExists{aasjournal.bst}{\bibliographystyle{aasjournal}}{\bibliographystyle{plainnat}}
\bibliography{references}
```

O arquivo consolidado `fase2/references.bib` corresponde ao nome solicitado por `\bibliography{references}` quando a bibliografia é resolvida a partir de `fase2`. A escolha de estilo é condicional: `aasjournal` se disponível, `plainnat` caso contrário. Os 56 registros possuem `author`, `title` e `year`; os anos desconhecidos são textuais (`s.d.`), apropriados à convenção solicitada. A presença de `url` é compatível com o fallback `plainnat` e com os pacotes `url`/`hyperref` do texto; a formatação efetiva de DOI/URL e eventuais sufixos para autores institucionais com o mesmo ano depende do `.bst` selecionado.

**A biblioteca contém 56 fontes, mas a seleção normal de BibTeX desse `.tex` contém apenas as 44 citadas**, pois não há `\nocite{*}`. A preservação das outras 12 entradas não exige inseri-las no texto nem gera citação por si só.

## 6. Fechamento

**Totais finais:** 56 referências únicas; 44 citadas; 12 não citadas; 0 citações sem entrada; 1 duplicata eliminada; 15 ausências de ano editorial representadas como `s.d.`; 1 inadequação estrutural corrigida; 0 novas divergências de identidade bibliográfica detectadas. As 8 limitações de fundamentação da tabela permanecem explícitas e não são convertidas em resultados publicados do sistema.

As edições foram feitas exclusivamente via `apply_patch` nos dois arquivos desta entrega. O `.tex`, os arquivos de pesquisa e os demais documentos não foram editados. A verificação foi por leitura/confronto textual, sem compilação e sem scripts.

### Verificação final complementar da entrega

Depois da auditoria bibliográfica, o relatório foi revisado para incorporar decisões operacionais e compilado com pdflatex/BibTeX, seguido de duas passagens LaTeX. O build final usa `plainnat` porque `aasjournal.bst` não está disponível no ambiente; manteve-se o fallback declarado no fonte. Não há citações/referências indefinidas nem caixas overfull no build aprovado. O PDF tem31páginas A4; figura de arquitetura foi inspecionada em renderização.

`scripts/verificar_documentos.py` confere unicidade de chaves, cobertura11etapas/C20/W12/O18/F24, pesquisas integrantes por saída/falha, seções do template e links locais. `scripts/gerar_entrega.py` compila e valida CRC/SHA-256 dos documentos no ZIP. Isso confirma integridade documental, não desempenho do EduAgent-OS. As contagens finais permanecem56fontes/44citadas e alcance de leitura declarado na auditoria.
