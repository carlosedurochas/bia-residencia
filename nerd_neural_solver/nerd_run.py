"""Executa um script do repositório NeRD (NVlabs/neural-robot-dynamics) com o PyTorch atual.

Os modelos pré-treinados do NeRD foram salvos como objetos Python completos (torch.save(model)).
A partir do PyTorch 2.6, o torch.load só aceita, por padrão, pesos e tipos conhecidos
(weights_only=True). Em vez de desligar essa proteção, este lançador libera apenas as 20 classes
que os checkpoints usam (listadas com torch.serialization.get_unsafe_globals_in_checkpoint) e
roda o script original sem modificá-lo.

Uso:
    python nerd_run.py <script relativo ao repositório> [argumentos do script]
    python nerd_run.py eval/eval_passive/eval_passive_motion.py --env-name Cartpole ...
"""

import os
import runpy
import sys

NERD_DIR = os.environ.get("NERD_DIR", r"C:\nerd")
sys.path.insert(0, NERD_DIR)

import numpy as np
import torch

from models.base_models import MLPBase
from models.model_transformer import GPT, MLP, Block, CausalSelfAttention, GPTConfig, LayerNorm
from models.models import MLPDeterministic, ModelMixedInput
from utils.running_mean_std import RunningMeanStd

torch.serialization.add_safe_globals(
    [
        # Arquitetura do NeRD (código do próprio repositório)
        ModelMixedInput, MLPDeterministic, MLPBase, RunningMeanStd,
        GPT, GPTConfig, Block, CausalSelfAttention, LayerNorm, MLP,
        # Módulos padrão do PyTorch
        torch.nn.GELU, torch.nn.ReLU, torch.nn.ModuleDict, torch.nn.ModuleList,
        torch.nn.Sequential, torch.nn.Dropout, torch.nn.Linear, torch.nn.Embedding,
        # Tipos do NumPy usados nas estatísticas de normalização
        np.core.multiarray.scalar, np.dtype,
        *(type(np.dtype(t)) for t in (np.float32, np.float64, np.int32, np.int64, np.bool_)),
    ]
)

if len(sys.argv) < 2:
    sys.exit(__doc__)

script = os.path.join(NERD_DIR, sys.argv[1])
sys.argv = [script] + sys.argv[2:]
os.chdir(os.path.dirname(script))  # os scripts do NeRD usam caminhos relativos à própria pasta
runpy.run_path(script, run_name="__main__")
