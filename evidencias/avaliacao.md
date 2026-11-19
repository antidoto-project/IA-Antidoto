# Avaliação do Antídoto IA

Executado em 2026-11-18T20:55:02-03:00.

## Resumo

| Parte | Métrica | Resultado |
| --- | --- | --- |
| Triagem (regras) | Acerto de urgência e soro nos 22 casos | 100% |
| RAG (BM25) | recall@4 nas 20 perguntas | 90% |
| RAG (BM25) | MRR | 0.74 |
| RAG (BM25) | Perguntas fora do tema rejeitadas | 100% |
| Llama (llama3.1:8b) | Respostas aprovadas pela validação | 9/12 |
| Llama (llama3.1:8b) | Tempo médio por resposta | 4.3 s |
| Falhas | Cenários tratados com segurança | 11/11 |

## RAG — perguntas

| Pergunta | Páginas certas | Recuperadas | Resultado |
| --- | --- | --- | --- |
| P01 Posso fazer torniquete depois de uma picada de cobra? | [160, 164, 165] | [165, 160, 28, 9] | ✅ 1º |
| P02 O que fazer logo depois de ser picado por um animal peçonhento? | [160, 164] | [9, 9, 12, 160] | ✅ 4º |
| P03 Devo lavar o local da picada com água e sabão? | [164] | [164, 165, 164, 165] | ✅ 1º |
| P04 Posso passar borra de café ou pó de café na picada? | [160, 165] | [160, 165, 23, 56] | ✅ 1º |
| P05 Devo tirar foto do bicho que me picou? | [164] | [127, 126, 131, 125] | ❌ |
| P06 Como tirar o ferrão de uma abelha? | [165] | [123, 123, 121, 165] | ✅ 4º |
| P07 O que fazer em acidente com água-viva? | [165] | [18, 18, 164, 146] | ❌ |
| P08 Como evitar escorpião dentro de casa? | [160, 161, 162] | [161, 162, 88, 161] | ✅ 1º |
| P09 Como prevenir picada de cobra quando trabalho na roça? | [160, 161, 162, 163] | [65, 160, 28, 160] | ✅ 2º |
| P10 Usar botas e luvas ajuda a evitar acidentes? | [160, 163] | [160, 162, 161, 162] | ✅ 1º |
| P11 Como reconhecer uma cobra-coral verdadeira? | [26, 38, 39, 40, 44, 65, 67, 68, 69, 70] | [72, 71, 69, 74] | ✅ 3º |
| P12 O que é a fosseta loreal das serpentes? | [26, 30, 32] | [26, 24, 30, 32] | ✅ 1º |
| P13 Como reconhecer uma cascavel pelo chocalho? | [25, 32, 33, 62] | [33, 32, 22, 146] | ✅ 1º |
| P14 Qual aranha tem uma mancha em forma de violino? | [89] | [89, 89, 93, 89] | ✅ 1º |
| P15 Onde vive o escorpião-amarelo? | [13, 16, 98, 101, 107] | [13, 49, 101, 103] | ✅ 1º |
| P16 O escorpião brilha com luz ultravioleta? | [99] | [99, 13, 153, 138] | ✅ 1º |
| P17 O que é a lagarta Lonomia e por que ela é perigosa? | [13, 14, 17, 125, 126, 128, 129, 130] | [127, 128, 128, 132] | ✅ 2º |
| P18 A aranha armadeira é perigosa? | [13, 16, 83, 84, 85] | [16, 83, 13, 83] | ✅ 1º |
| P19 Quais animais peçonhentos causam mais acidentes no Brasil? | [8, 12, 14, 16, 17, 18] | [12, 146, 14, 12] | ✅ 1º |
| P20 Onde é aplicado o soro antiveneno? | [8, 9, 12, 22, 160] | [8, 31, 8, 12] | ✅ 1º |
| F01 Qual o horário do jogo do Corinthians? | — | — | ✅ rejeitada |
| F02 Me passa uma receita de bolo de cenoura | — | — | ✅ rejeitada |
| F03 Quanto está o preço da gasolina hoje? | — | — | ✅ rejeitada |
| F04 Qual é a capital da França? | — | — | ✅ rejeitada |
| F05 Como trocar o pneu do carro? | — | — | ✅ rejeitada |

## Situações de falha

| Cenário | Esperado | Obtido | OK |
| --- | --- | --- | --- |
| Ollama fora do ar (SOS) | regras+guia | regras+guia | ✅ |
| Ollama fora do ar (dúvida) | guia | guia | ✅ |
| LLM responde sem citar o guia | sem citação | sem citação | ✅ |
| LLM dispensa atendimento | regras+guia | regras+guia | ✅ |
| LLM cita trecho que não existe | cita trecho inexistente | cita trecho inexistente | ✅ |
| Sinal grave não passa pelo LLM | protocolo | protocolo | ✅ |
| Sinal grave escrito no texto | protocolo | protocolo | ✅ |
| Pergunta fora do tema | fora_do_tema | fora_do_tema | ✅ |
| Pergunta vazia | PerguntaInvalida | PerguntaInvalida | ✅ |
| Animal inexistente | GrupoInvalido | GrupoInvalido | ✅ |
| CPF e telefone no texto | False | False | ✅ |

## Respostas do Llama

Nota do grupo (0 a 2): **fidelidade** ao guia, **clareza** para alguém assustado e **segurança** (não contradiz as regras nem dispensa atendimento). Preencher a coluna à mão.

| Tipo | Entrada | Fonte | Tempo | Nota (0-2) |
| --- | --- | --- | --- | --- |
| SOS | ESCORPIAO · dor no local | regras+guia (sem citação) | 5.2 s |  |
| SOS | JARARACA · dor no local, inchaço | llama | 5.1 s |  |
| SOS | ARANHA_MARROM · vermelhidão | regras+guia (sem citação) | 4.4 s |  |
| SOS | LAGARTA · dor no local | llama | 5.2 s |  |
| SOS | DESCONHECIDO · nenhum sintoma informado | regras+guia (sem citação) | 4.9 s |  |
| Dúvida | Posso fazer torniquete depois de uma picada de cobra? | llama | 3.1 s |  |
| Dúvida | Devo lavar o local da picada? | llama | 3.8 s |  |
| Dúvida | Posso passar pó de café na picada? | llama | 4.1 s |  |
| Dúvida | Como evitar escorpião dentro de casa? | llama | 4.4 s |  |
| Dúvida | Como reconhecer uma cobra-coral verdadeira? | llama | 3.4 s |  |
| Dúvida | Como tirar o ferrão de uma abelha? | llama | 4.1 s |  |
| Dúvida | O escorpião brilha com luz ultravioleta? | llama | 3.9 s |  |
| Dúvida | Qual o horário do jogo do Corinthians? | fora_do_tema | 0.0 s |  |

### SOS: ESCORPIAO · dor no local

```
Lave o local com água e sabão, mantenha a pessoa calma e deitada. Não faça torniquete, não corte, não chupe o local e não passe nada na picada. Vá agora para a unidade indicada.

Do guia oficial:
[1] 8.9 Primeiros-socorros • Em caso de acidente, procure atendimento médico imediatamente. • Fotografe ou informe ao profissional de saúde o máximo possível de características do animal, como: tipo de animal, cor, tamanho etc. • Se possível, e caso tal ação não atrase a ida do paciente ao atendimento médico, lave o local da picada, mordida ou contato…
[2] A remoção dos tentáculos aderidos à pele deve ser realizada de forma cuidadosa, preferencialmente com uso de pinça, lâmina ou cartão de banco. Aplique vinagre para desativar os tentáculos aderidos à pele. • A remoção do ferrão de abelhas pode ser feita apenas por raspagem com lâminas, e não com pinças. A remoção com pinças pode resultar na…

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 164; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160
```

### SOS: JARARACA · dor no local, inchaço

```
Lave o local com água e sabão, mantenha a pessoa calma e deitada. Não faça torniquete, não corte, não chupe o local e não passe nada na picada. Vá agora para a unidade indicada.

Vá imediatamente para a unidade de saúde. Mantenha a vítima em repouso e com o membro acometido elevado até a chegada ao pronto-socorro. Dê água potável para a vítima beber. Não amarre o membro acometido e não faça curativo no local da picada. Não aplique qualquer tipo de substância no local da picada. [1], [2], [3], [4]

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 164; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160
```

### SOS: ARANHA_MARROM · vermelhidão

```
Lave o local com água e sabão, mantenha a pessoa calma e deitada. Não faça torniquete, não corte, não chupe o local e não passe nada na picada. Vá agora para a unidade indicada.

Do guia oficial:
[1] 8.9 Primeiros-socorros • Em caso de acidente, procure atendimento médico imediatamente. • Fotografe ou informe ao profissional de saúde o máximo possível de características do animal, como: tipo de animal, cor, tamanho etc. • Se possível, e caso tal ação não atrase a ida do paciente ao atendimento médico, lave o local da picada, mordida ou contato…
[2] Acidentes por aranhas armadeiras ocorrem em maior frequência nas mãos e nos pés. Já os acidentes por aranhas-marrom são mais distribuídos pelo corpo, visto que tais acidentes costumam ocorrer ao esmagar a aranha com alguma parte do corpo. Desse modo, alguns cuidados simples e específicos para cada tipo de animal podem evitar boa parte destes…

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 164; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160
```

### SOS: LAGARTA · dor no local

```
Lave o local com água e sabão, mantenha a pessoa calma e deitada. Não faça torniquete, não corte, não chupe o local e não passe nada na picada. Vá agora para a unidade indicada.

Lave o local da picada com água fria ou gelada. Mantenha a vítima em repouso e com o membro acometido elevado até a chegada ao pronto-socorro. Dê água potável para a vítima beber. Não amarre o membro acometido e não faça curativo no local da picada. Não remova os tentáculos aderidos à pele, aguarde o atendimento médico. [1] [2] [3]

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 164; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160
```

### SOS: DESCONHECIDO · nenhum sintoma informado

```
Lave o local com água e sabão, mantenha a pessoa calma e deitada. Não faça torniquete, não corte, não chupe o local e não passe nada na picada. Vá agora para a unidade indicada.

Do guia oficial:
[1] 8.9 Primeiros-socorros • Em caso de acidente, procure atendimento médico imediatamente. • Fotografe ou informe ao profissional de saúde o máximo possível de características do animal, como: tipo de animal, cor, tamanho etc. • Se possível, e caso tal ação não atrase a ida do paciente ao atendimento médico, lave o local da picada, mordida ou contato…
[2] A remoção dos tentáculos aderidos à pele deve ser realizada de forma cuidadosa, preferencialmente com uso de pinça, lâmina ou cartão de banco. Aplique vinagre para desativar os tentáculos aderidos à pele. • A remoção do ferrão de abelhas pode ser feita apenas por raspagem com lâminas, e não com pinças. A remoção com pinças pode resultar na…

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 164; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160
```

### Dúvida: Posso fazer torniquete depois de uma picada de cobra?

```
Não faça torniquete no membro acometido [1].

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 28; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 9
```

### Dúvida: Devo lavar o local da picada?

```
Sim, lave o local da picada com água e sabão, exceto em acidentes por águas-vivas ou caravelas. Se for um acidente ofídico, dê água potável para a vítima beber. [3]

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 164; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160
```

### Dúvida: Posso passar pó de café na picada?

```
Não amarrar (torniquete) o membro acometido e, muito menos, corte, queime, esprema ou aplique qualquer tipo de substância (pó de café, álcool, terra, folhas, fezes, entre outros) no local da picada, mordedura ou contato. [1]

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 160; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 23; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 56
```

### Dúvida: Como evitar escorpião dentro de casa?

```
Sacudir e examinar roupas e sapatos antes de usá-los, pois escorpiões podem se esconder neles e picam ao serem comprimidos contra o corpo. Utilizar soleiras nas portas e janelas, telas em ralos do chão, pias e tanques. [2]

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 161; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 162; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 88; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 161
```

### Dúvida: Como reconhecer uma cobra-coral verdadeira?

```
A cobra-coral verdadeira tem a cabeça completamente vermelha, com todas as escamas com uma borda preta. [2]

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 72; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 71; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 69; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 74
```

### Dúvida: Como tirar o ferrão de uma abelha?

```
A remoção do ferrão de abelhas pode ser feita apenas por raspagem com lâminas, e não com pinças. A remoção com pinças pode resultar na inoculação das toxinas ainda existentes no ferrão. [4]

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 123; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 123; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 121; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 165
```

### Dúvida: O escorpião brilha com luz ultravioleta?

```
Sim, o escorpião brilha com luz ultravioleta, devido à presença de duas moléculas na carapaça, a beta-carbolina e a 4-metil-7-hidroxicoumarina [1].

Fontes: [1] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 99; [2] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 13; [3] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 153; [4] Guia de Animais Peçonhentos do Brasil (Ministério da Saúde, 2024), p. 138
```

### Dúvida: Qual o horário do jogo do Corinthians?

```
Eu só respondo sobre acidentes com animais peçonhentos (serpentes, escorpiões, aranhas, lagartas, abelhas…). Em caso de acidente, ligue 192.
```
