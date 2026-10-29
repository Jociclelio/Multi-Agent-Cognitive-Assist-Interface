# Task 001: Definir corpus, autorizações e desvios aceitáveis das metas

Estado: aguardando revisão
Depende de: nenhuma
Origem: nenhuma

## Prompt
Fechar as questões abertas do plano 06 e do protocolo (seção "Questões abertas" de ambos) ANTES de qualquer coleta de dados: (1) Confirmar a disponibilidade real do corpus candidata e as autorizações/licenças de uso das duas disciplinas (uma técnico-formal, outra conceitual), registrando a fonte de cada material e a autorização correspondente — sem redistribuir materiais sem permissão. (2) Escolher e justificar as duas disciplinas concretas. (3) Definir, por escrito e antes da coleta, os desvios aceitáveis das metas de quantidade propostas (24 famílias documentais, 120 consultas e 120 tentativas por conjunto, 30 trajetórias com 8 sessões, 100+100 instâncias de agenda, ≥10 casos base por falha F01–F24) — as quantidades são metas propostas a conferir por disponibilidade/autorização, não requisitos fechados, e o desvio aceitável precisa existir antes de se olhar qualquer resultado. (4) Decidir o juiz LLM (qual modelo, para triagem/secundária apenas) com plano de calibração contra humanos, e decidir se haverá medição de energia (só reportar se houver medidor/contador identificado; senão `N/A` com motivo). Registrar todas as decisões com justificativa na task; se alguma decisão exigir ajuste no texto normativo de `fase2/documentos/06_protocolo_de_avaliacao.md`, corrigir apenas em dif mínimo com justificativa.

Restrições: nada apresentado como resultado medido; as metas de quantidade nunca são apresentadas como resultados; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar se o documento 06 for alterado; commit de entrega (se houver alteração de artefatos) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — protocolo normativo (etapa 6): seção 2 (dados e desenho, metas de quantidade) e questões abertas do próprio documento.
- `.agents/plans/06-protocolo-de-avaliacao/plan.md` — seção "Questões abertas" com as quatro pendências que esta task fecha.
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — origem dos IDs F01–F24 (casos base por falha) e O01–O18.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — contexto da v0.1 implementada (conectores opcionais, gates) para avaliar o que o corpus precisa exercitar.

## Corretude
- [x] C1 — As duas disciplinas estão escolhidas com justificativa e cada material do corpus tem fonte e autorização/licença registradas; nada é redistribuído sem permissão. Escolha fechada nesta task com confirmação do usuário (ver Decisões D1/D2); registro **por material** (fonte, data, hash, tipo de uso) pertence à coleta da task 002, que herda estas decisões. O modelo de autorização adotado (uso privado, sem redistribuição) honra "não redistribuir sem permissão" por construção; a ausência de autorização de redistribuição está registrada como pendência condicional do usuário, não presumida como obtida.
- [x] C2 — Desvios aceitáveis das metas de quantidade definidos por escrito ANTES da coleta, para cada conjunto (famílias, consultas/tentativas, trajetórias, agenda, casos de falha); as metas permanecem rotuladas como propostas. Ver Decisões D4, registradas nesta task antes de qualquer coleta; metas seguem rotuladas como propostas em protocolo §2, plan e mapa 08 §8.
- [x] C3 — Juiz LLM decidido com plano de calibração contra humanos (uso restrito a triagem/secundária) e decisão sobre energia registrada (medidor identificado ou `N/A` com motivo); decisões registradas na task e, se aplicável, ajuste em dif mínimo no documento 06 com verificador passando. Ver Decisões D5 (juiz) e D6 (energia). Nenhum ajuste no documento 06 foi necessário: as quatro decisões cabem no texto normativo vigente (ver D7); verificador `passed` reproduzido após as alterações.

## Execução
- Modelo: GLM-5.3-Flash (provedor `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime.
- Base: d816a38
- Entrega: fb6afd94f2078cf6b3ab30daf7013598e0b4ed2f (`.gitignore` + `eval/corpus/README.md`; documento 06 e demais artefatos normativos sem dif)
- Arquivos da entrega: `.gitignore`, `eval/corpus/README.md`
- Evidências: ver seção Decisões abaixo e os comandos registrados em Evidências de verificação.

## Notas

### Decisões (fecham as questões abertas do plano 06 e do protocolo, antes de qualquer coleta)

#### D1 — Disciplinas escolhidas
- **Técnico-formal: Redes de Computadores** (graduação). Justificativa: densidade de fatos exatos e estruturados — cabeçalhos/protocolos, campos, portas, tabelas, parâmetros de configuração e cronogramas — exercita extração exata (O01), ontologia de entidades e conflito de versões (O02), códigos e temporalidade das consultas, e os perturbadores de F01 (tabela/sinal/data alterados) e F02 (datas e revisões conflitantes). Exige explicitamente scans e tabelas no material depositado.
- **Conceitual (respostas abertas): Aprendizado Não Supervisionado** (graduação). Justificativa: admite itens interpretativos sem resposta única — interpretação de resultados de agrupamento, comparação e justificativa de escolha de método, discussão de limitações — exercitando rubricas 0–4 (O04/O07), validade de itens (O05), julgamento formativo (O08) e falso acerto.
- **Ressalva registrada:** a disciplina do slot conceitual também contém conteúdo quantitativo. A coleta do slot privilegiará questões interpretativas de resposta aberta; se o piloto de desenvolvimento (teste da rubrica) mostrar predominância de itens de resposta fechada, a substituição dessa disciplina será decidida e registrada **antes do congelamento**, nunca silenciosamente.
- Confirmação: os autores confirmaram por consulta nesta sessão que possuem materiais das duas disciplinas (PDD, cronogramas e material didático liberado ao longo do semestre).

#### D2 — Modelo de autorização e pendências de usuário
- Modelo registrado: **uso privado pelos autores** para o projeto (eles cursaram as disciplinas e possuem os arquivos-fonte); **sem redistribuição na publicação** — serão publicados apenas hashes, IDs, manifestos, exemplos sintéticos e instruções de acesso, coerente com protocolo §7 ("datasets autorizados/anotações ou referências de acesso") e mapa 08 (anotação: "corpus restrito é entregue por hashes e instruções de acesso autorizado").
- Com isso, "não redistribuir materiais sem permissão" (protocolo §2) é honrado por construção: originais ficam em `eval/corpus/originais/` (ignorado pelo Git, nunca commitado).
- **Pendência condicional do usuário (registrada, não presumida):** não há autorização de redistribuição obtida dos donos dos materiais e nenhuma foi presumida. Se em qualquer momento for necessário redistribuir originais ou anotações verbatim, a autorização escrita deve ser obtida antes. O manifesto do corpus (task 002) registrará essa condição junto ao tipo de uso de cada material.
- Registro por material (fonte, data de obtenção, tipo, SHA-256, vínculo de versão) pertence à coleta da task 002, que herda estas decisões.

#### D3 — Local de depósito do corpus
- `eval/corpus/originais/<disciplina>/`, fora do Git (regra adicionada ao `.gitignore`), com regras de registro em `eval/corpus/README.md` (novo). Originais imutáveis após a coleta; alteração gera novo registro com hash.

#### D4 — Desvios aceitáveis das metas de quantidade (por escrito, antes da coleta)
Metas (protocolo §2 e mapa 08 §8) permanecem **propostas**, não requisitos fechados nem resultados. Faixas de desvio aceitáveis, fixadas antes de qualquer coleta:

| Conjunto | Meta proposta | Desvio aceitável | Regra |
|---|---|---|---|
| Famílias documentais | 24 (8 dev/4 val/12 test; 12 por disciplina) | ≥18 no total; mínimos por split: dev ≥6, val ≥3, test ≥9; ≥5 por disciplina | Manter ≥2 scans e ≥2 tabelas no total. Abaixo dos mínimos: não iniciar anotação; registrar indisponibilidade |
| Consultas | 120 por conjunto (80 com suporte/40 sem) | ≥96 por conjunto | Proporção com/sem suporte mantida entre 60% e 70% de com suporte; ≥40 por conjunto por disciplina |
| Tentativas | 120 por conjunto (60 por disciplina) | ≥90 por conjunto | ≥40 por disciplina por conjunto; níveis de ajuda e erros anotados em todas as tentativas |
| Trajetórias longitudinais | 30 teste + 6 dev + 4 val, 8 sessões cada | teste ≥24, dev ≥4, val ≥3 | Nº de sessões mantido em 8 (estrutura do roteiro é fixa); se insuficiente, reduzir nº de trajetórias e declarar potência limitada — nunca encurtar roteiro silenciosamente |
| Agenda | 100 pequenas + 100 realistas, split 40/20/40 | ≥60 pequenas + ≥60 realistas | Proporções 40/20/40 aproximadas (±5 p.p.); casos de zona/bordas presentes em todos os splits — sem borda, F13 fica sem casos |
| Casos de falha | ≥10 por F01–F24; 3 seeds com geração; crashpoints determinísticos | ≥6 por falha | Manter 3 seeds quando há geração e crashpoints determinísticos sem redução; nenhuma F01–F24 sem caso base — falha inaplicável à v0.1 vira `N/A` com motivo, nunca omissão |

Regra geral: desvio além destas faixas é registrado com justificativa nas tasks 002/003 **antes do congelamento**; nenhum desvio é decidido após observar escores; amostra abaixo do previsto reporta IC e resultado inconclusivo em vez de reduzir critério (protocolo §3). Essas faixas são tolerâncias do plano de coleta, não thresholds da matriz de avaliação.

#### D5 — Juiz LLM (triagem/secundária apenas)
- Papel: triagem e pontuação secundária; **nunca** gera ouro e nunca sustenta gate primário (humanos são ouro de conteúdo); o Monitor do sistema não é ouro da própria avaliação.
- Modelo: **distinto do modelo do sistema** (Bonsai 2 27B local). Candidato concreto: modelo via API já disponível ao projeto (GLM, provedor `sd2`), com alternativa local documentada (modelo maior que o SUT no mesmo servidor, custo de VRAM/latência registrado e custo de juiz reportado separado, como o relatório técnico §5 já exige). O pino final — identificador de modelo/revisão, prompt, hash, política de abstinência — é registrado no congelamento da validação (mapa 08 §9: "modelo/prompt/hash separados"); sem trocar juiz depois de olhar teste.
- Plano de calibração contra humanos (antes de qualquer uso em teste): (1) em desenvolvimento/validação, anotadores humanos avaliam pacotes cegos (sem condição, sem trace de identidade, sem parecer do Monitor); (2) o juiz avalia os mesmos pacotes com a mesma rubrica e referência; (3) acordo medido por dimensão, tipo de erro, disciplina, nível de ajuda e comprimento; (4) controles de viés do §6/mapa 08 §9: ordem A/B contrabalanceada, versão prolixa sem conteúdo novo, paráfrases, respostas idênticas, rótulos MA/SA ocultos, com registro de flips e efeito de comprimento; (5) meta de acordo: nível comparável às rubricas humanas, com **valor-alvo fixado no piloto de desenvolvimento e congelado antes do teste** — nenhum número é inventado aqui, para não criar threshold novo; (6) se a calibração não sustentar pontuação secundária, o juiz fica restrito a triagem binária ou é descartado, com decisão registrada antes da coleta de teste.

#### D6 — Energia
- **Há medidores/contadores identificados** na máquina atual de execução: RAPL Intel (domínios `package-0`, `core` e `dram` em `/sys/class/powercap/`) e NVML (`nvidia-smi`, RTX 3060, `power.draw`/`power.limit` verificados nesta sessão).
- Decisão: a reportagem de energia é **esperada** quando a plataforma de execução fixada expuser esses contadores; escopo registrado (CPU package e GPU amostrada; não cobre o restante do sistema). O mecanismo de coleta pertence à etapa 7 e sua implementação à etapa 8.
- Limites verificados nesta sessão: leitura de `energy_uj` exige root/grupo especial — se a permissão não puder ser garantida na plataforma final, ou se a plataforma não expuser contador (ou consumo de API), energia = `N/A` com motivo, conforme protocolo §5. O `N/A` passa a ser exceção justificada, não padrão.

#### D7 — Ajustes no documento 06: nenhum, justificado
Nenhuma das decisões contradiz o texto normativo: D1/D2 cabem no §2 (corpus de duas disciplinas com registro de licença/autorização e não redistribuição — o modelo de uso privado sem redistribuição é compatível com a redação), D4 já é previsto ("quantidades são metas propostas... conferidas por disponibilidade/autorização"), D5 já está no §6 ("juiz LLM... triagem e pontuação secundária após calibração contra humanos") e D6 segue §5 ("energia só se medidor/contador identificado"). Alterar o documento sem necessidade violaria a regra de dif mínimo; portanto, dif zero no documento 06 e no mapa da etapa 4.

### Pendências de usuário
1. Depositar os PDFs das duas disciplinas em `eval/corpus/originais/` (estrutura em `eval/corpus/README.md`) antes da task 002; registro por material é feito na coleta.
2. Pendência condicional de autorização: se publicação/compartilhamento vier a exigir redistribuição de originais ou anotações verbatim, obter autorização escrita dos donos dos materiais antes (D2).

### Evidências de verificação
- `python3 fase2/scripts/verificar_documentos.py` (da raiz, após as alterações): `"status": "passed"` — 11 etapas, 20 componentes, 18 saídas, 24 falhas, 39 links locais, `delivery_pending` vazio.
- Contadores de energia verificados nesta sessão: `ls /sys/class/powercap/` → `intel-rapl` com domínios `package-0`/`core`/`dram`; `nvidia-smi --query-gpu=name,power.draw,power.limit` → RTX 3060, ~165,9 W / limite 170 W; `energy_uj` exige root (limite registrado em D6).
- `git check-ignore -v eval/corpus/originais/teste.pdf` → regra `.gitignore:46` ativa (originais fora do Git).
- Nada medido do EduAgent-OS: as decisões são pré-experimentais; as faixas de D4 são tolerâncias de plano de coleta, não resultados.

### Dificuldade esperada
4/10 — Decisões pré-experimentais com dependência externa (autorização de materiais); o risco é deixar uma questão aberta implícita e descobrir depois da coleta.

### Dificuldade sentida
3/10 — As quatro decisões exigiram conciliar restrições já normativas (protocolo, mapa 08, relatório técnico) sem inventar thresholds, e a dependência externa (autorização/disciplinas) foi resolvida por consulta direta ao usuário em duas rodadas. A parte de maior cuidado foi desenhar faixas de desvio por conjunto que preservem a análise estatística do plano (splits, clusters, ICs) sem ampliar metas nem criar números novos para calibração do juiz — o valor-alvo de acordo ficou deliberadamente para o piloto.

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: —
- Decisão: —
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/06-protocolo-de-avaliacao/plan.md)
