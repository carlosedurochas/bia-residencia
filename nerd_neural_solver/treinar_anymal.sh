#!/usr/bin/env bash
# Treina um NeRD do zero para o quadrúpede ANYmal no WSL2 (ou Linux), com a configuração dos autores
# (train/cfg/Anymal/transformer.yaml), mudando só o número de iterações e os caminhos dos dados.
#
# Uso:
#   bash treinar_anymal.sh <nome do treino> <épocas> [iterações por época]
#   bash treinar_anymal.sh treino_curto_6k 15 400        # 5.600 iterações (a época 0 só avalia)
#   bash treinar_anymal.sh treino_autores 1001 5000      # 5 milhões, como os autores
#   DADOS=5M bash treinar_anymal.sh treino_240k_5M 601 400   # com o conjunto de 5 milhões de transições
#
# Espera o repositório do NeRD em ~/nerd_ws/nerd e o ambiente Python em ~/envs/nerd.
set -euo pipefail

NAME=${1:?nome do treino}
EPOCHS=${2:?número de épocas}
ITERS=${3:-400}
WORKERS=${WORKERS:-8}
DADOS=${DADOS:-1M}  # tamanho do conjunto de treino, em milhões de transições: 1M, 5M, 10M...

source ~/envs/nerd/bin/activate
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH:-}  # biblioteca CUDA do driver do Windows
export NERD_DIR=$HOME/nerd_ws/nerd
RUN="$(cd "$(dirname "$0")" && pwd)/nerd_run.py"
ENV=AnymalJointPositionControl
DATA=$HOME/nerd_ws/data/datasets/$ENV
TRAIN=$DATA/trajectory_len-100_${DADOS}_train.hdf5
VALID=$DATA/trajectory_len-100_valid.hdf5
LOGDIR=$HOME/nerd_ws/data/trained_models/Anymal/$NAME

# 1. Dados: trajetórias de 100 passos com ações aleatórias nas juntas e contato com o chão,
#    simuladas pelo solver analítico (gerados só uma vez; o gerador pergunta antes de sobrescrever)
[ -f "$TRAIN" ] || python "$RUN" generate/generate_dataset_anymal.py --env-name $ENV --num-transitions "${DADOS%M}000000" \
    --dataset-name "$(basename "$TRAIN")" --trajectory-length 100 --num-envs 2048 --seed 0
[ -f "$VALID" ] || python "$RUN" generate/generate_dataset_anymal.py --env-name $ENV --num-transitions 200000 \
    --dataset-name "$(basename "$VALID")" --trajectory-length 100 --num-envs 2048 --seed 10

# 2. Treino (a pasta de saída precisa ser nova)
if [ -e "$LOGDIR" ]; then echo "A pasta $LOGDIR já existe; use outro nome." >&2; exit 1; fi
python "$RUN" train/train.py --cfg ./cfg/Anymal/transformer.yaml --logdir "$LOGDIR" --no-time-stamp \
    --cfg-overrides "algorithm.num_epochs $EPOCHS algorithm.num_iters_per_epoch $ITERS \
algorithm.dataset.num_data_workers $WORKERS algorithm.dataset.train_dataset_path $TRAIN \
algorithm.dataset.valid_datasets.exp_trajectory $VALID algorithm.eval.dataset_path $VALID"
