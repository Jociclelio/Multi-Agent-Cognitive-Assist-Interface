# Etapa 3 — Síntese da pesquisa metodológica de implementação

## Método e documentos integrantes

Esta etapa é uma revisão técnica dirigida pelos vinte requisitos, realizada em 30/09/2026. Foram orquestradas duas frentes de pesquisa com consulta a fontes primárias, artigos e documentação oficial. Não se trata de revisão sistemática nem de prova de ótimo global. Os relatórios integrais, incluindo procedimentos, alternativas, referências e tentativas malsucedidas, são parte deste documento:

1. [`../pesquisa/03a_arquitetura_rag.md`](../pesquisa/03a_arquitetura_rag.md): C01–C05, C13–C17 e C20; 18 núcleos bibliográficos.
2. [`../pesquisa/03b_pedagogia_memoria_planejamento.md`](../pesquisa/03b_pedagogia_memoria_planejamento.md): C06–C12; 18 itens, com alcance de leitura discriminado.

As bibliografias dessas frentes ficam em `../pesquisa/references_arquitetura.bib` e `../pesquisa/references_pedagogia.bib`. C18–C19 são completados pela pesquisa específica das etapas 6–7. Esta síntese não deve ser distribuída sem os relatórios integrantes; o pacote final inclui todos.

## Decisões reconciliadas

| Componentes | Método selecionado para a primeira implementação | Referências/chaves | Por que e sob qual limite |
|---|---|---|---|
| C01/C20 | GGUF Bonsai 2 27B, fork Prism de llama.cpp, servidor único e manifesto completo | `bonsai2`, `bonsaidemo`, `llamasrv`, `uvlock` | Identidade rastreável; dados do fornecedor não substituem teste local. PTQ1_0 é ensaio inicial, PQ2_0 alternativa |
| C02/C03 | Docling, OCR seletivo, blocos com página/origem, ontologia relacional e fatos candidatos | `docling`, `ocrpdf`, `pydstrict` | Permite conferir números, datas e citações; confirmação prevalece sobre confiança verbal |
| C04 | BM25 + BGE-M3 denso, RRF explícito e reranker opcional | `m3`, `rrf09`, `qdranthyb`, `bgerank` | Recupera literais e paráfrases; parâmetros e benefício precisam de validação em português |
| C05 | Curadoria com estados de conteúdo realmente acessado | `ytcaptions`, `mcpsec` | Metadados de vídeo não autorizam resumo da transcrição; provedor conectado é configurável |
| C06 | Skills versionadas, estados de tentativa/pista/autoexplicação/transferência | `chi1994selfexplanation`, `roediger2006testing`, `sun2025multitutor`, `wang2023voyager` | Apoio contingente e recuperação ativa; não importar eficácia de outro domínio/população |
| C07/C08 | Gabarito/rubrica antes da avaliação, verificação formal quando possível, estado observado; BKT em modo experimental | `kim2024prometheus`, `farquhar2024semanticentropy`, `badrinath2021pybkt` | Evita transformar erro do juiz em domínio do aluno; estimador exige logs/calibração |
| C09/C10 | Eventos originais, fatos temporais, projeções versionadas, recuperação antes de síntese | `packer2023memgpt`, `wu2025longmemeval` | Preserva correções e ajuda recebida; compressão não é presumida sem perdas |
| C11 | Blocos candidatos e CP-SAT; verificador independente | `google2024cpsat`, `googleEmployeeScheduling`, `gou2024tora` | Viabilidade verificável; prazo/duração mal interpretados continuam sendo erro upstream |
| C12 | ICS UTC, UID persistente; conector remoto com outbox/reconciliação | `desruisseaux2009icalendar`, `daboo2007caldav`, `google2026calendarcreate` | Offline fecha o núcleo; UID não garante deduplicação em todo importador manual |
| C13/C14 | LangGraph, snapshots, Pydantic/JSON Schema, MCP nas fronteiras | `hong2024metagpt`, `lgstate`, `lginterrupt`, `mcparch`, `pydstrict` | Roteamento explícito, pausa e retomada; A2A não é dependência interna |
| C15/C16 | Autorização por código, escritor único, SQLite/WAL, idempotência e outbox | `mcpsec`, `sqlitewal`, `lginterrupt` | Checkpoint não é commit de domínio; timeout externo requer reconciliação |
| C17 | Traces locais, métricas e limites ativos | `oteltrace`, `llamasrv` | Identifica custo e loops; traces não são provas de correção |
| C18/C19 | Ouro independente, splits por família, avaliação pareada, ablações e falhas injetadas | Pesquisa específica na etapa 7 | Seleção de parâmetros em validação, nunca no teste final |

## Conflitos de parâmetros resolvidos para a etapa 4

- Janela operacional inicial de 32.768 tokens, não a janela máxima anunciada. Reservas únicas: saída 16.384, ferramentas 2.048 e margem 1.024; entrada máxima 13.312. A reserva cobre geração de raciocínio e resposta quando aplicável. Se o hardware não comportar, o perfil deve ser revalidado; não combinar simultaneamente a regra percentual da frente pedagógica com essas reservas.
- Evidências documentais até 4.096 tokens; memória até oito unidades, com limite de 2.048 tokens. O limite de entrada total prevalece sobre limites locais.
- Solver: sete dias, slots conservadores de quinze minutos e dez segundos **totais** entre etapas lexicográficas. `FEASIBLE` não é prova de ótimo; `UNKNOWN` não é inviável.
- Aprendizagem: estimativa numérica `null` no MVP; três respostas independentes de famílias distintas permitem apenas rótulo provisório de evidência favorável. Intervalos 1/3/7 dias são política de ensaio, não uma lei de retenção.
- Grafo: seis chamadas LLM, oito ferramentas, dezesseis transições, dois reparos globais e um por artefato; 120 s de computação ativa por turno. Jobs de ingestão são separados.

Todos esses números são escolhas iniciais configuráveis. O teste de desenvolvimento determina viabilidade; a configuração é congelada antes do teste final. A extensão de agenda remota permanece atrás de feature flag até a documentação específica e os ensaios de concorrência serem concluídos.

## Limites da base bibliográfica

Metadados foram acessados, mas não o texto integral de Wood, Corbett e RRF; Chi foi acessado pelo resumo editorial. Os relatórios distinguem precisamente esses casos. A formulação operacional de RRF é sustentada também pela documentação oficial; BKT é descrito a partir do texto acessível de pyBKT. MetaGPT é referenciado pela versão arXiv consultada, sem afirmar uma verificação editorial que falhou. Não foi reaproveitada a bibliografia preliminar da fase 1, que contém entradas não verificadas.
