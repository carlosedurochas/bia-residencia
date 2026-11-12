# Como o NeRD é treinado

Guia de leitura do processo de treino do NeRD (*Neural Robot Dynamics*), usando o **Cartpole** como exemplo, porque é
o caso mais simples: dois graus de liberdade e nenhum contato. Os links apontam para as cópias do código em
[`nerd_codigo/`](nerd_codigo/), com os números de linha.

## A ideia em uma frase

O NeRD aprende por **imitação do simulador analítico**. O solver analítico (Featherstone, no Warp Sim) gera milhões
de exemplos "estado atual + comando → próximo estado", e a rede aprende, por regressão supervisionada, a prever a
**variação** do estado em cada passo.

```
 1. Gerar dados             2. Montar exemplos         3. Treinar
 ───────────────            ──────────────────         ───────────────────────
 estados iniciais e         trajetórias cortadas       Transformer prevê a
 comandos aleatórios   ──►  em janelas de 10    ──►    variação do estado;
 simulados pelo solver      passos; alvo = próximo     perda = erro quadrático
 analítico (HDF5)           estado − estado atual      contra o solver analítico
```

## Passo 1: gerar os dados com o solver analítico

Arquivos: [`generate_dataset_contact_free.py`](nerd_codigo/generate/generate_dataset_contact_free.py) e
[`trajectory_sampler.py`](nerd_codigo/generate/trajectory_sampler.py#L67) (`sample_trajectories_joint_act_mode`).

Comando usado pelos autores:

```bash
python generate_dataset_contact_free.py --env-name Cartpole --num-transitions 1000000 \
    --dataset-name trajectory_len-100_1M_train.hdf5 --trajectory-length 100 --num-envs 2048 --seed 0
```

O que acontece, em rodadas de 2.048 ambientes simulados em paralelo na GPU:

1. **Estados iniciais aleatórios.** Cada ambiente começa num estado sorteado de forma uniforme dentro de faixas fixas
   ([`commons.py`](nerd_codigo/utils/commons.py#L30)):
   - posição do carrinho entre −3,5 e 3,5 m e ângulo do pêndulo entre −π e π, ou seja, qualquer ângulo, inclusive de cabeça para baixo;
   - velocidades entre −10 e 10.
2. **Comandos aleatórios a cada passo.** Para cada um dos 100 passos é sorteado um comando novo e independente:
   a atuação no carrinho fica entre −1.500 e 1.500, e o pêndulo não é atuado (`JOINT_ACT_SCALE = [1500, 0]`).
   São comandos sem intenção nenhuma: o objetivo é cobrir o máximo de situações, não executar uma tarefa.
3. **Simulação analítica.** O ambiente roda 100 passos no modo `ground-truth`. Em cada passo, o amostrador guarda o
   estado atual, o comando, o próximo estado e, nos robôs com contato, as informações de contato.
4. **Limpeza.** Trajetórias que explodem numericamente (NaN, infinito ou valores acima de 10⁵) são descartadas.
5. **Salvamento.** Tudo vai para um arquivo HDF5. Um segundo conjunto, gerado com outra semente (`--seed 10`), serve
   para validação.

Resultado: cerca de **10.000 trajetórias de 100 passos (1 milhão de transições)**. No ANYmal, os autores usaram um
script próprio (`generate_dataset_anymal.py`), com contatos, e cerca de 20 milhões de transições.

## Passo 2: transformar trajetórias em exemplos de treino

Arquivo: [`datasets.py`](nerd_codigo/utils/datasets.py#L118) (`TrajectoryDataset`).

Como o modelo olha os últimos 10 passos, cada exemplo de treino é uma **janela de 10 passos consecutivos**. Cada
trajetória de 100 passos rende 91 janelas (passos 1–10, 2–11, …, 91–100), o que dá cerca de **910 mil janelas** no
Cartpole ([`build_index`](nerd_codigo/utils/datasets.py#L162)).

O [`SequenceModelTrainer`](nerd_codigo/algorithms/sequence_model_trainer.py) é só isso: o mesmo laço de treino do
`VanillaTrainer`, trocando o conjunto de dados pelas janelas.

## Passo 3: preparar entradas e alvos

Arquivo: [`vanilla_trainer.py`](nerd_codigo/algorithms/vanilla_trainer.py#L278) (`preprocess_data_batch`).

Para cada lote de janelas:

- **Entradas:** passam pelo mesmo processamento usado na simulação (`process_neural_model_inputs`), com conversão de
  referencial e máscara de contatos. Isso garante que a rede veja, no treino, exatamente o mesmo formato de entrada
  que verá ao simular. No Cartpole, a entrada por passo é o estado (4 números: posição e velocidade do carrinho,
  ângulo e velocidade do pêndulo) e o comando (2 números).
- **Alvo:** é a variação do estado, calculada a partir dos dados
  ([`convert_next_states_to_prediction`](nerd_codigo/integrators/integrator_neural.py#L711)):
  `alvo = próximo estado − estado atual`, com os ângulos ajustados para o intervalo [−π, π]. Na orientação de robôs
  como o ANYmal, o alvo é a rotação (quaternion) entre a orientação atual e a próxima.

Prever a variação em vez do próximo estado completo facilita o aprendizado: num passo de simulação o estado muda
pouco, e a rede só precisa aprender essa pequena diferença.

## Passo 4: normalizar

Arquivo: [`vanilla_trainer.py`](nerd_codigo/algorithms/vanilla_trainer.py#L233) (`compute_dataset_statistics`).

Antes do treino, o treinador percorre todo o conjunto de treino e calcula a **média e o desvio padrão** de cada
entrada e do alvo. Esses valores ficam guardados dentro do modelo (`set_input_rms`, `set_output_rms`) e são usados
sempre, no treino e na simulação. É por isso que os checkpoints carregam a classe `RunningMeanStd`.

Sem isso, valores em escalas muito diferentes atrapalhariam o treino: posições na casa dos metros, velocidades na
casa das dezenas e variações por passo bem menores.

## Passo 5: calcular a perda

Arquivo: [`vanilla_trainer.py`](nerd_codigo/algorithms/vanilla_trainer.py#L304) (`compute_loss`).

1. O Transformer processa a janela inteira e devolve uma previsão para **cada um dos 10 passos**
   ([`forward`](nerd_codigo/models/models.py#L218)). Como a atenção é causal, a previsão do passo *k* só usa os passos
   1 a *k*. Assim, cada janela vira 10 exemplos, com históricos de 1 a 10 passos, e a rede aprende a funcionar mesmo
   quando ainda não há histórico completo, como no início de uma simulação.
2. A perda é o **erro quadrático médio** entre a previsão e o alvo, com cada saída dividida pelo desvio padrão do alvo.
   Na prática, isso dá o mesmo peso a todas as componentes do estado, sejam elas grandes ou pequenas.
3. Para acompanhamento, o treinador também converte a previsão em próximo estado e registra o erro por componente.
   Isso não entra no gradiente.

## Passo 6: otimizar

Configuração em [`transformer.yaml`](nerd_codigo/train/cfg/Cartpole/transformer.yaml); laço em
[`one_epoch`](nerd_codigo/algorithms/vanilla_trainer.py#L355).

| Item | Valor no Cartpole |
|---|---|
| Otimizador | Adam |
| Taxa de aprendizado | Cai linearmente de 1e-3 para 1e-4 ao longo do treino |
| Lote | 512 janelas |
| Iterações por "época" | 5.000 |
| Épocas | 1.000 |
| Corte de gradiente | Norma máxima 1,0 |

Aqui uma "época" não é uma passada completa pelos dados, e sim 5.000 lotes (cerca de 2,6 milhões de janelas, perto
de 3 passadas pelo conjunto do Cartpole). O treino completo tem 5 milhões de iterações. O README dos autores não
informa quanto tempo isso leva.

## Passo 7: validar e escolher o modelo

Arquivo: [`vanilla_trainer.py`](nerd_codigo/algorithms/vanilla_trainer.py#L439) (`train`).

A cada época, o treinador mede o modelo de duas formas e salva o melhor de cada uma:

- **Perda de validação:** a mesma perda do treino, calculada no conjunto gerado com outra semente.
- **Avaliação por simulação** (`eval: mode: sampler`): roda o modelo como solver por 10 passos, em 2.048 trajetórias
  novas com comandos aleatórios, e compara com o solver analítico. É o mesmo tipo de teste que fizemos na replicação,
  só que com horizonte de 10 passos.

A segunda medida existe por causa de uma diferença importante entre treino e uso:

- **No treino**, todas as entradas da janela vêm dos dados, ou seja, são estados corretos do solver analítico
  (*teacher forcing*). Um erro num passo não contamina o seguinte.
- **Na simulação**, a rede recebe as próprias previsões como entrada do passo seguinte, e os erros se acumulam.

Uma perda de treino baixa não garante uma simulação estável; por isso a avaliação por simulação é a mais próxima do uso real.

## Resumo

| Etapa | Cartpole |
|---|---|
| Fonte dos dados | Solver analítico Featherstone (Warp Sim), sem dado real |
| Volume | 1 milhão de transições (10.000 trajetórias × 100 passos) |
| Como os dados variam | Estados iniciais e comandos sorteados de forma uniforme |
| Exemplo de treino | Janela de 10 passos, uma previsão por passo |
| Entrada por passo | Estado (4) + comando (2) |
| Alvo | Variação do estado até o próximo passo |
| Perda | Erro quadrático médio, normalizado por componente |
| Modelo | Transformer de 6 camadas, 2,7 M de parâmetros |
| Escolha do modelo | Melhor erro em simulação de 10 passos e melhor perda de validação |

## O que observar se for treinar um

- **O modelo só conhece o que foi sorteado.** As faixas do Passo 1 definem onde o NeRD é confiável. Estados fora delas,
  como velocidades acima de 10, não aparecem no treino.
- **O modelo herda o solver.** O alvo é sempre o próximo estado do Featherstone; se o solver analítico errar em
  relação ao mundo real, o NeRD aprende o mesmo erro.
- **A versão do simulador importa.** Os modelos do Ant e do pêndulo foram treinados com dados do Warp 1.5.1, e a
  replicação usou o 1.8.0, o que explica parte do erro maior do Ant.
