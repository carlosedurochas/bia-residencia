# Código relevante do NeRD

Cópia, sem modificações, dos arquivos do [NVlabs/neural-robot-dynamics](https://github.com/NVlabs/neural-robot-dynamics)
(commit `370e89d`, de 10/11/2025) que explicam como o solver neural substitui o analítico. O código é da NVIDIA, sob a
licença Apache 2.0 ([LICENSE.md](LICENSE.md)), e mantém os caminhos do repositório original.

Esta pasta serve para **leitura**. Os arquivos importam outros módulos do repositório que não foram copiados, então
não rodam daqui. Para executar, use o repositório completo em `C:\nerd` com o [`../nerd_run.py`](../nerd_run.py).

## Por onde começar

A ideia central está em dois trechos:

1. **A troca de solver** ([`envs/neural_environment.py`](envs/neural_environment.py), `set_env_mode`, linha 314).
   O ambiente guarda os dois integradores e só troca qual deles o simulador usa a cada passo:
   `integrator_gt` (o analítico do Warp Sim) ou `integrator_neural` (o NeRD). Cena, robô e controle não mudam.
2. **O passo do solver neural** ([`integrators/integrator_neural.py`](integrators/integrator_neural.py), `simulate`, linha 329).
   Tem a mesma assinatura do integrador analítico (`model`, `state_in`, `state_out`, `dt`, `control`). Em vez de
   resolver as equações de dinâmica e contato, ele:
   1. monta a entrada da rede com o estado atual, o histórico, os torques das juntas e os contatos (`get_neural_model_inputs`);
   2. converte a entrada para o referencial definido em `states_frame` no `cfg.yaml` (`convert_coordinate_frame`).
      No ANYmal é `body`, o referencial do próprio robô, que torna o modelo invariante à posição e à direção no mundo;
      no Cartpole, que só se move num trilho, é `world`;
   3. prevê a *variação* do estado (`neural_model.evaluate`);
   4. soma a variação ao estado atual e volta para o referencial do mundo (`convert_prediction_to_next_states`, `convert_states_back_to_world`);
   5. recalcula a posição de cada corpo com a cinemática direta (`eval_fk`), exatamente como o solver analítico faria.

## Mapa dos arquivos

| Arquivo | Papel |
|---|---|
| **Solver neural** | |
| [`integrators/integrator_neural.py`](integrators/integrator_neural.py) | `NeuralIntegrator`: o "solver" neural. Monta a entrada, chama a rede e converte a previsão no próximo estado |
| [`integrators/integrator_neural_stateful.py`](integrators/integrator_neural_stateful.py) | Acrescenta memória de estados anteriores |
| [`integrators/integrator_neural_transformer.py`](integrators/integrator_neural_transformer.py) | `TransformerNeuralIntegrator`: o usado pelos modelos pré-treinados; passa os últimos 10 estados para o Transformer |
| **Rede neural** | |
| [`models/model_transformer.py`](models/model_transformer.py) | Transformer no estilo GPT (atenção causal sobre o histórico de estados) |
| [`models/models.py`](models/models.py) | `ModelMixedInput`: codifica as entradas (estado, torques, contatos, gravidade) e normaliza entradas e saídas |
| [`models/base_models.py`](models/base_models.py) | MLPs usados nos codificadores e na cabeça de saída |
| [`pretrained_models/.../Cartpole/model/cfg.yaml`](pretrained_models/NeRD_models/Cartpole/model/cfg.yaml) | Configuração do modelo do Cartpole: 6 camadas, 12 cabeças, dimensão 192, histórico de 10 estados, previsão relativa |
| [`pretrained_models/.../Anymal/model/cfg.yaml`](pretrained_models/NeRD_models/Anymal/model/cfg.yaml) | Configuração do modelo do ANYmal |
| **Ambiente e comparação** | |
| [`envs/neural_environment.py`](envs/neural_environment.py) | `NeuralEnvironment`: o ambiente com os dois solvers e a troca entre eles; também grava os vídeos |
| [`envs/warp_sim_envs/env_cartpole.py`](envs/warp_sim_envs/env_cartpole.py) | Definição do Cartpole no Warp Sim (o lado analítico) |
| [`envs/warp_sim_envs/env_anymal.py`](envs/warp_sim_envs/env_anymal.py) | Definição do ANYmal no Warp Sim |
| [`utils/evaluator.py`](utils/evaluator.py) | `NeuralSimEvaluator`: gera trajetórias de referência com o solver analítico, roda o NeRD dos mesmos estados iniciais e calcula o erro (`calculate_error`) |
| [`eval/eval_passive/eval_passive_motion.py`](eval/eval_passive/eval_passive_motion.py) | Script do teste de movimento passivo (métricas e vídeos do Cartpole e do pêndulo) |
| [`eval/eval_rl/run_rl.py`](eval/eval_rl/run_rl.py) | Script que roda uma política de RL em qualquer um dos solvers (teste e vídeo do ANYmal) |
| **Treino** (explicado passo a passo em [`../guia_treino_nerd.md`](../guia_treino_nerd.md)) | |
| [`generate/generate_dataset_contact_free.py`](generate/generate_dataset_contact_free.py) | Gera o conjunto de dados do Cartpole com o solver analítico e salva em HDF5 |
| [`generate/trajectory_sampler.py`](generate/trajectory_sampler.py) | `TrajectorySampler`: sorteia estados iniciais e ações e simula as trajetórias |
| [`generate/simulation_sampler.py`](generate/simulation_sampler.py) | `WarpSimDataGenerator`: classe base do amostrador (faixas de sorteio, sorteio uniforme ou Sobol) |
| [`utils/commons.py`](utils/commons.py) | Faixas de sorteio de cada robô (`JOINT_Q_MIN`, `JOINT_QD_MAX`, `JOINT_ACT_SCALE`...) |
| [`utils/datasets.py`](utils/datasets.py) | `TrajectoryDataset`: corta as trajetórias em janelas de 10 passos |
| [`train/train.py`](train/train.py) | Ponto de entrada do treino |
| [`train/cfg/Cartpole/transformer.yaml`](train/cfg/Cartpole/transformer.yaml) | Configuração de treino do Cartpole (dados, otimizador, arquitetura) |
| [`algorithms/sequence_model_trainer.py`](algorithms/sequence_model_trainer.py) | `SequenceModelTrainer`: o treinador usado com o Transformer; só troca o conjunto de dados pelas janelas |
| [`algorithms/vanilla_trainer.py`](algorithms/vanilla_trainer.py) | `VanillaTrainer`: o laço de treino em si (alvos, normalização, perda, otimização, validação) |
