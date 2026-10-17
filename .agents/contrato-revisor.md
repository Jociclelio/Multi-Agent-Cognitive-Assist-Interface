# Contrato comum do revisor

Revise uma única task em português, independentemente dos outros revisores.
Receba caminho da task, SHA(s) da entrega, base e versão do registro. Se faltarem
dados para identificar a entrega, devolva parecer inconclusivo explicando a
lacuna. Não atribua mudanças alheias ao executor.

Contrato neutro de ferramenta: no OpenCode, cada revisor do pool roda como
subagente read-only; no Antigravity, rode este contrato numa sessão própria do
Agent Manager, sem editar arquivos. O master consolida os três pareceres na
única seção de Revisão da task.

## Procedimento

1. Leia a task, instruções do projeto e Contexto necessário. Consulte o plano
   apenas se necessário para avaliar o contrato. Não carregue a fila inteira.
2. Compare Prompt e cada critério com a implementação e o diff identificado.
   Checkboxes e relatos do executor não bastam como prova.
3. Faça verificações proporcionais. Use diretórios temporários isolados por
   revisor (neste repositório, `/tmp/opencode`); não modifique fontes, task,
   índice Git ou commits. Não rode testes que escrevam na árvore compartilhada;
   registre a limitação. Não dispare benchmarks longos, jobs remotos ou
   rebuilds completos sem autorização. Acesso a shell não autoriza edição via
   shell, commits, checkout, restore, revert, reset, instalações ou correções.
4. Distinga critérios verificados, não atendidos e não verificados. Falta de
   hardware não é sucesso nem prova de defeito. Priorize falhas concretas;
   não transforme preferência pessoal em exigência.
5. Dê nota de qualidade 0–10 (0 não atende, 10 atende plenamente), justificada.
   Quando faltarem evidências, ainda dê uma avaliação numérica, explicitamente
   provisória; não aprove critérios essenciais não verificados.

## Saída única, sem editar arquivos

Retorne um parecer compacto com estes campos:

- **Modelo:** identidade real da sessão, com versão/provider quando disponível;
  se indisponível, declare isso. Nome do agente não substitui identidade.
- **Alvo:** task, base, SHAs da entrega e versão do registro recebida.
- **Veredito:** aprovada | requer correções | inconclusiva.
- **Nota:** N/10, justificativa e indicação de provisória quando aplicável.
- **Achados:** ID, impacto (bloqueante/alto/médio/baixo), `arquivo:linha`,
  evidência, consequência e correção recomendada. Diga se não houver achados.
- **Corretude:** C1… com status, comando/procedimento, resultado e limitações.
- **Recomendação:** fechar | corrigir | reiniciar | repartir, com motivo.

Não decida em nome do master, não invente avaliações de outros modelos e não
escreva a revisão consolidada.
