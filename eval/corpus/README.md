# Corpus restrito da etapa 6 — local de depósito

Este diretório acomoda o corpus autorizado do protocolo de avaliação
(`fase2/documentos/06_protocolo_de_avaliacao.md`, seção 2). O material original
das disciplinas é restrito e **não é versionado nem redistribuído**: o
subdiretório `originais/` está ignorado pelo Git e os originais permanecem
apenas na máquina local dos autores.

## Disciplinas escolhidas (task 001 do plano 06)

- **Técnico-formal:** Redes de Computadores (graduação).
- **Conceitual (respostas abertas):** Aprendizado Não Supervisionado (graduação),
  com coleta de itens privilegiando questões interpretativas de resposta aberta.

## Estrutura de depósito

```
eval/corpus/originais/redes-de-computadores/   # ignorado pelo Git
eval/corpus/originais/aprendizado-nao-supervisionado/   # ignorado pelo Git
```

 Depositar PDFs digitais, scans, tabelas e versões conflitantes em subpastas por
 disciplina. Nenhum arquivo em `originais/` deve ser commitado em hipótese
 alguma.

## Regras de registro (executadas na task 002, antes do uso)

Cada material depositado recebe registro com: disciplina, origem/fonte, data de
obtenção, tipo de material (PDF digital, scan, tabela, versão), SHA-256 dos
bytes e vínculo de versão. O modelo de uso registrado é o seguinte:

- **Uso privado pelos autores** para o projeto EduAgent-OS (etapa 6 e seguintes);
  os autores cursaram as disciplinas e possuem os arquivos-fonte.
- **Sem redistribuição na publicação**: o que se publica são hashes, IDs,
  manifestos, exemplos sintéticos e instruções de acesso — nunca os originais
  nem anotações verbatim deles derivadas (protocolo, seção 7; mapa da etapa 8,
  seção de anotação).
- **Pendência condicional registrada**: não há autorização de redistribuição
  obtida dos donos dos materiais. Se em qualquer momento for necessário
  redistribuir originais ou anotações verbatim, a autorização escrita deve ser
  obtida **antes** — este registro não a substitui.

Alterações no material original depois da coleta geram novo registro (novo
hash); nada é substituído silenciosamente após o congelamento dos splits.
