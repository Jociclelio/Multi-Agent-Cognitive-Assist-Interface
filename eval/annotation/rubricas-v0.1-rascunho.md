# Rubricas 0–4 para saídas semênticas — rascunho v0.1 (piloto pendente)

Status: **rascunho, ainda não testado em piloto**. A versão deste arquivo é
`v0.1-rascunho`; o piloto no split de desenvolvimento (task 003 do plano 06,
critério C1) **não foi executado** por ausência de dois avaliadores humanos
independentes (ver `README.md` nesta pasta). Nenhum ajuste de rubrica foi
registrado porque nenhum piloto ocorreu; **esta rubrica não pode ser usada no
split de teste antes do piloto e dos ajustes registrados** (protocolo de
avaliação, seção 2). Nada aqui é resultado medido.

Referências normativas:
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 2 (anotação) e seção 3 (O04, O07, O08).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §3.2 (forma do item de rubrica:
  `criterion_id, description, levels, critical, evidence_refs`), §3.4 (`AnnotationRecord`) e §4 (anotação com piloto em dev, acordo antes da adjudicação).
- `.agents/tasks/06-protocolo-de-avaliacao/001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md` — decisão D5 (juiz LLM nunca gera ouro; humanos são ouro de conteúdo).

## Condições de uso (quando o piloto ocorrer)

- Anotação por **dois avaliadores humanos independentes, cegos à arquitetura e
  à condição** (sem rótulo MA/SA, sem trace de identidade, sem parecer do
  Monitor); mapa `blind_artifact_id → run` oculto aos anotadores.
- Cada anotação registra um `AnnotationRecord` (mapa 08, §3.4):
  `blind_artifact_id, evaluator_id_pseudonym, rubric_version, dimension/criterion,
  label, spans, reason, certainty_category, annotated_at`.
- Acordo (kappa) medido **antes** da adjudicação; discordâncias vão a
  adjudicação por terceiro; normas de texto NFC/espaços e sinais preservados
  (mapa 08, §4).
- Os IDs O04, O07 e O08 são permanentes (origem:
  `fase2/documentos/05_fluxos_resultados_e_falhas.md`) e não são renumerados.

## Rubrica RUB-O04 — resposta tutoria (saída semêntica, quatro dimensões)

Aplica-se a respostas tutoriais avaliadas em O04 (protocolo, seção 3: "Rubrica
humana 0–4 por dimensão; claim correctness e apoio; erro crítico"). Cada
dimensão é um item de rubrica independente, com âncoras comuns abaixo.

Âncoras gerais da escala 0–4 (ajustáveis apenas no piloto, com ajuste
registrado antes do uso no teste):

| Nível | Âncora genérica |
|---|---|
| 0 | Contraria o ouro ou fabrica conteúdo (fato, fonte ou citação inexistente); inutiliza a resposta |
| 1 | Majoritariamente incorreto ou inadequado à dimensão; falhas não são marginais |
| 2 | Parcialmente correto/adequado; falhas relevantes que um leitor atento precisa corrigir |
| 3 | Correto/adequado com imprecisões menores que não induzem a erro |
| 4 | Correto/adequado e completo para o nível da pergunta, sem ressalvas necessárias |

### RUB-O04-CORRETUDE — `critical: true`

Corretude factual e conceitual frente ao ouro (`required_claims`, `critical_facts`).
Nível 0 obrigatório quando a resposta fabrica fato/fonte ou contradiz claim
crítica do ouro. Erro crítico nesta dimensão bloqueia o sucesso do caso
(protocolo, seção 3, O04: "erro crítico bloqueia sucesso").

### RUB-O04-PERTINENCIA — `critical: false`

A resposta endereça a pergunta feita (e não outra pergunta próxima). Nível 0
quando responde tema diverso do perguntado; nível 4 quando cobre os aspectos
pedidos sem expansão irrelevante.

### RUB-O04-CLAREZA — `critical: false`

Organização, terminologia consistente com o material (português com termos
técnicos ingleses) e ausência de ambiguidade. Nível 0 quando a formulação
induz a erro factual; nível 4 quando um aluno do curso lê sem esforço de
reconstrução.

### RUB-O04-LIMITES — `critical: true`

Reconhecimento de incerteza e de limites do material: não apresenta inferência
como fato do documento; abstenção ou pedido de esclarecimento quando o
indecidível aparece (protocolo, seção 4, F04/F06). Nível 0 quando afirma com
confiança algo que o ouro não sustenta; nível 4 quando sinaliza limites
exatamente onde existem, sem abstenção indevida.

## Rubrica RUB-O07 — contingência do apoio (saída semêntica)

Aplica-se a O07 (protocolo, seção 3: "Rubrica 0–4 de contingência; taxas de
vazamento, insistência e espera correta"). A rubrica 0–4 mede a contingência
do apoio ao aluno; as taxas (vazamento, insistência, término) são contagens à
parte, não níveis desta rubrica.

| Nível | Âncora — contingência do apoio |
|---|---|
| 0 | Revela solução/gabarito sem origem registrada, ignora terminal legítimo do aluno ou insiste contra pedido explícito |
| 1 | Apoio desconectado do estado do aluno; avança sem diagnosticar o erro |
| 2 | Apoio parcialmente contingente; erra o nível de ajuda (dica além do necessário ou insuficiente para o estado demonstrado) |
| 3 | Apoio contingente com deslize pontual de timing ou forma |
| 4 | Apoio ajustado ao estado demonstrado do aluno; mantém a solução fechada até reveal legítimo; respeita terminal e espera corretamente |

`RUB-O07-CONTINGENCIA` é `critical: true` no nível 0 (vazamento de verso/gabarito
contraria O06/O07: "zero verso vazado antes de reveal").

## Rubrica RUB-O08 — julgamento formativo (apoio ao O08)

O08 usa kappa ponderado por critério e macro-F1 de erros (protocolo, seção 3).
Os itens de anotação associados, para uso humano (o juiz LLM só triagem/secundária,
decisão D5):

- `RUB-O08-JULGAMENTO` — a avaliação formativa emitida sobre a tentativa está
  correta frente ao ouro (`criterion_labels`, `misconception_codes`): escala
  0–4 com as âncoras genéricas de RUB-O04; `critical: true` no nível 0
  (falso acerto crítico: tratar resposta errada como acerto).
- `RUB-O08-ERRO` — código de erro observado na tentativa, escolhido de
  taxonomia fechada registrada no ouro (`misconception_codes`); categorias
  mínimas do corpus atual: `factual`, `conceitual`, `procedural`, `temporal`,
  `nenhum`. Categoria `nenhum` exige `reason` preenchida.

## Anotação de tentativas — níveis de ajuda (categórica, não 0–4)

Conforme mapa 08, seção 12, cada tentativa recebe nível de ajuda anotado
(requisito da D4 para o conjunto de tentativas, "em todas as tentativas"):
`nenhuma | hint | reveal-parcial | reveal-total`, com `spans` da ajuda e
`evidence_refs` para o item de origem. Esta anotação é categórica e não usa a
escala 0–4; alimenta O05/O07/O09 e a análise de vazamento.

## O que falta antes do uso

1. **Piloto no split de desenvolvimento** com dois avaliadores humanos
   independentes cegos à arquitetura/condição (não executado; ver `README.md`).
2. **Ajustes de rubrica registrados** com a versão incrementada antes de
   qualquer uso no teste (protocolo, seção 2; nada de ajuste foi simulado aqui).
3. **Ouro humano** com IDs de fonte/claim, critérios/erros, fatos temporais e
   restrições originais — nunca derivado de saída do sistema avaliado nem
   gerado por juiz LLM (decisão D5).
4. **Kappa e adjudicação** registrados por dimensão/critério após dois
   julgamentos independentes.
