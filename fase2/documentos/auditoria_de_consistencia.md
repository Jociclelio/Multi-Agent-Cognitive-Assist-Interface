# Auditoria independente de consistência e fechamento

Uma revisão independente, somente leitura, confrontou os oito documentos metodológicos, quatro pesquisas, proposta e instruções da fase2. Verificou cobertura nominal C01–C20/W01–W12/O01–O18/F01–F24 e apontou quinze lacunas operacionais. Foram corrigidas nos mapas normativos, no relatório e nas notas de resolução das pesquisas. Este registro preserva o motivo das alterações sem apresentar verificações de implementação ainda não executadas.

| Achado | Decisão incorporada | Local vigente |
|---|---|---|
| Autoridade de snapshot/expected_version indefinida | domain_revision por usuário, materialização curta, approval_revision/dependências | mapa4 §15.1; mapa8 §12 |
| Rubrica sem critério→tópico e omissão sem span | topic_ids, evidence_kind missing/span=null, corretude por tópico | mapa4 §15.2; mapa8 §12 |
| Ordem/revisão/independência de tentativas ambíguas | occurred_at+ordinal, assessment vigente por revisão/supersedes, independência na sessão e replay | mapa4 §§8/15.2; mapa8 O09/§12 |
| Elo evidência→agenda sem política | policyv1 due/prioridade/duração/confirmação/dedup explícitas | mapa4 §15.3; mapa8 §12 |
| Predecessor concluído/iniciado/outside-horizon | Dependência de atividade tipada; fixos e términos reais | mapa4 §15.4; mapa8 §12 |
| Grade/limite diário/alcance de INFEASIBLE |00:00 por dia local, minutos reservados, informar inviável na grade | mapa4 §15.5; mapa8 §12 |
| Identidade de bloco/UID/revisão ICS | occurrence persistente, event_sequence só mudança do evento | mapa4 §15.5; relatório |
| Incumbent perdido em etapa posterior UNKNOWN | conservar solução anterior/provas parciais/FEASIBLE | mapa4 §15.5; mapa8 §12 |
| Approve/progresso sem rota completa | approve_plan e ActivityUpdate com status/recibo | mapa4 §§10/15.4; relatório |
| Ownership e dependências não expressos em esquema | FK composta/owner, artifact_dependencies e política backup30dias | mapa4 §15.1; mapa8 §12 |
| Metas sem orçamento de execução/anotação | Inventário/alvos por disciplina, dev/val longitudinal, piloto20 e orçamento runs/horas/amostra | mapa8 §12.1; relatório |
| Comparação de instruções reduzidas e delegação incompletas | Contraste mesma skill full/reduced e handoff válido consumido; estimativa probabilística explicitamente adiada | mapa4 §15.6; mapa8 §§5/12; relatório |
| Cobertura nominal sem requisito→teste | requirements emCaseRecord, matrizC→predicado e validator | mapa8 §12.2 |
| Pesquisas históricas conflitavam com correções | Hierarquia normativa e notas de resolução no início das quatro pesquisas | mapa4 §1; pesquisas3a/3b/7a/7b |
| Lakens contextualizado como artigo não lido | Referência ao livro/capítulo efetivamente consultado, DOI e representação misc | mapa8 §11; references.bib; auditoria10 |

## Limitações que permanecem próprias de uma metodologia

Não foram executados o modelo/runtime, OCR/RAG, o pipeline educacional nem o testbed. Pin final de dependências e hardware é gate de instalação explicitamente prescrito. Corpus real/autorização, ouro e calibração dependem de coleta; N e potência são planejados por piloto, não demonstrados. Durações/prioridades iniciais são política de engenharia a avaliar, não ótimo pedagógico. Simulações não comprovam aprendizagem humana. Inviabilidade vale para a grade; UID não deduplica todo cliente e sync não promete exactly-once. Exclusão ensaiada é lógica, não sanitização física; SIGKILL não representa queda elétrica. Leitura parcial de algumas fontes e documentação móvel permanece registrada.

Essas condições têm comportamento implementável: capacidade não admitida resulta em erro tipado/feature desabilitada; dado não confirmado permanece candidato; estimativa probabilística fica null; métrica indefinida fica N/A/null com motivo. Não foram substituídas pendências por resultados inventados.
