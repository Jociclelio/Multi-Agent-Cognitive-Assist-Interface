# Task 002: Manifesto/hardware e gate de modelo Bonsai 2 (mapa §3.1, §13.1)

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Implementar o gate de modelo do mapa §3.1 e §13.1: candidato `prism-ml/Ternary-Bonsai-2-27B-gguf`, revisão `b072e1d3b35a0a630cece372c2127528e0994386`, arquivo inicial `Ternary-Bonsai-2-27B-PTQ1_0.gguf`, SHA publicado `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3`. Conferir SHA local, licença e NOTICE. Runtime obrigatório: fork `PrismML-Eng/llama.cpp`, release candidata `prism-b10743-adfffbe`, capacidade verificada e fixada por hash (não presumir compatibilidade do stock llama.cpp). Implementar o adaptador `generate(messages, schema, sampler, deadline, seed) -> GenerationResult` (texto final, contagens, finish_reason, erro tipado; pensamento não é fonte de evidência) e servidor loopback com um slot e fila de quatro pedidos. Rodar os gates de aceite: carregamento offline, tokenizer, JSON e ferramentas negadas; primeiro modo non-thinking com sampling `.7/.8/20/min_p=0`; comparar thinking `1/.95/20/.05` apenas em desenvolvimento. JSON schema solicitado somente se o fork suportar; parse/schema/política permanecem obrigatórios. Se o candidato não carregar ou falhar gates: marcar `MODEL_NOT_ADMITTED`, sem substituição silenciosa. Registrar versões reais (pacotes, modelo, tokenizer) em `manifest.json` e atualizar `uv.lock`.

Se o download/carregamento for inviável no hardware local (tamanho, VRAM/RSS), registrar o impedimento documentado com os passos reproduzíveis e o estado do gate como pendente de hardware — não fingir sucesso nem trocar de modelo.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §3.1 (modelo) e §13.1 (primeira etapa da sequência com gate próprio).
- `config/default.yaml` (task 001) — limites de janela e timeouts usados nos gates.

## Corretude
- [ ] C1 — Adaptador `generate` implementado com a assinatura do mapa e erro tipado; servidor loopback com um slot e fila de quatro; nenhum acesso à rede além do download pinado.
- [ ] C2 — Gates executados com evidência registrada (comandos, saída, SHA conferido); resultado `MODEL_ADMITTED` com perfil non-thinking (ou `MODEL_NOT_ADMITTED`/pendente de hardware documentado, sem substituição).
- [ ] C3 — `manifest.json` registra versões reais de pacotes, modelo, tokenizer e hash do runtime; `uv.lock` atualizado.
- [ ] C4 — Mapa intocado; commits de entrega e registro separados; temporários em `/tmp/opencode`; submódulo não tocado.

## Notas

### Dificuldade esperada
6/10 — Dependência de runtime externo (fork), download grande e gates de hardware; risco de inviabilidade local deve virar bloqueio documentado, não improviso.

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
