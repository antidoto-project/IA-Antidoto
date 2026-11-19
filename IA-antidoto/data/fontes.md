# Fontes de dados

| Arquivo | Fonte | Responsável | Licença / uso | Acessado em |
| --- | --- | --- | --- | --- |
| `docs/guia_animais_peconhentos_brasil.pdf` | http://bvsms.saude.gov.br/bvs/publicacoes/guia_animais_peconhentos_brasil.pdf | Ministério da Saúde · Secretaria de Vigilância em Saúde e Ambiente (2024) | Creative Commons Atribuição – Não Comercial – Compartilha Igual (uso acadêmico, sem fins comerciais, com atribuição) | 16/11/2026 |

## Bases criadas pelo grupo

| Arquivo | Origem | Observação |
| --- | --- | --- |
| `soros.json` | Mesmos códigos de grupo e soro da API .NET do Antídoto; nomes dos soros conforme o Ministério da Saúde | Surucucu usa o soro antibotrópico-laquético (SABL); `DESCONHECIDO` fica sem soro e a unidade decide |
| `casos-triagem.json` | Regras de urgência da API .NET do Antídoto | 22 casos: os 9 grupos, os 7 sinais graves, maiúsculas/minúsculas e lista vazia |
| `documentos.json` | Grupo | Páginas do PDF que entram no índice: ficam de fora capa, sumário, aberturas de capítulo, tabelas de espécies (p. 46–47) e referências bibliográficas |
| `perguntas-avaliacao.json` | Grupo, conferido no texto do guia | 20 perguntas com as páginas que as respondem + 5 perguntas fora do tema |

Nenhuma base tem dado pessoal. As conversas gravadas no SQLite passam pela máscara de CPF, telefone e e-mail.
