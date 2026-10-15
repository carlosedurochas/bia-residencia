#!/usr/bin/env bash
# Tira a foto do Spot no MuJoCo MJX (WSL2). Argumentos extras são repassados ao script.
set -e
# No WSL o libcuda.so fica em /usr/lib/wsl/lib, fora do caminho padrão de busca
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$LD_LIBRARY_PATH
source ~/envs/mjx/bin/activate
python "$(dirname "$0")/spot_photo.py" "$@"
