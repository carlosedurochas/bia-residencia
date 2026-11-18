"""Compara os treinos de 240 mil iterações do NeRD no ANYmal com 1 e com 5 milhões de transições.

Gera duas figuras em results/:
  - comparacao_validacao_anymal.png: perdas de treino e de validação dos dois treinos no mesmo gráfico;
  - comparacao_passivo_anymal.png: erros do teste passivo de 100 passos (autores, 5M e 1M), lidos dos logs.

Uso:
    python plot_comparacao_dados.py
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = Path(__file__).resolve().parent / "results"
C5, C1, CA = "#7b52c7", "#3a9a3a", "#e08a1e"  # 5M, 1M, autores


def read(name):
    return re.sub(r"\x1b\[[0-9;]*m", "", (RES / name).read_text(encoding="utf-8", errors="ignore"))


def losses(log):
    text = read(log)
    train = [float(x) for x in re.findall(r"\[Train\] loss = ([0-9.eE+-]+)", text)]
    valid = [float(x) for x in re.findall(r"\[Valid\] dataset \[\w+\]: loss = ([0-9.eE+-]+)", text)]
    return train, valid


def passive(log):
    text = read(log)
    pos = float(re.search(r"Base position error mean\s*=\s*([0-9.eE+-]+)", text).group(1)) * 1000  # m -> mm
    ori = float(re.search(r"Base orientaion error mean.*?\(([0-9.]+) deg\)", text).group(1))
    jnt = float(re.search(r"Joint position error mean.*?\(([0-9.]+) deg\)", text).group(1))
    return pos, ori, jnt


# 1. Curvas de perda dos dois treinos
fig, ax = plt.subplots(figsize=(9, 5))
for log, color, label in [("treino_240k_5M_anymal.log", C5, "5 milhões de transições"),
                          ("treino_240k_anymal.log", C1, "1 milhão de transições")]:
    train, valid = losses(log)
    ax.plot(range(len(valid)), valid, color=color, lw=1.4, label=f"Validação, {label}")
    ax.plot(range(1, len(train) + 1), train, color=color, lw=1, ls="--", alpha=0.7, label=f"Treino, {label}")
ax.axvline(150, color="gray", lw=0.8, ls=":")
ax.text(153, 0.3, "época 150: validação\ncom 1M estaciona", fontsize=9, color="gray", va="top")
ax.set_yscale("log")
ax.set_xlabel("Época (400 iterações)")
ax.set_ylabel("Perda (erro quadrático normalizado)")
ax.set_title("NeRD no ANYmal, 240 mil iterações: efeito da quantidade de dados")
ax.grid(True, which="both", alpha=0.3)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(RES / "comparacao_validacao_anymal.png", dpi=130)

# 2. Erros do teste passivo de 100 passos
models = [("Autores\n(5 milhões de it.)", "passive_Anymal.log", CA),
          ("240 mil it.,\ndados 5M", "passive_Anymal_240k_5M_best_valid_exp_trajectory_model.log", C5),
          ("240 mil it.,\ndados 1M", "passive_Anymal_240k_best_valid_exp_trajectory_model.log", C1)]
values = [passive(log) for _, log, _ in models]
metrics = ["Posição da base (mm)", "Orientação da base (°)", "Juntas (°)"]
fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
for i, (ax, metric) in enumerate(zip(axes, metrics)):
    vals = [v[i] for v in values]
    bars = ax.bar([m[0] for m in models], vals, color=[m[2] for m in models])
    ax.bar_label(bars, labels=[f"{v:.2f}".replace(".", ",") if v < 10 else f"{v:.1f}".replace(".", ",") for v in vals],
                 padding=2, fontsize=10)
    ax.set_title(metric)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.tick_params(axis="x", labelsize=9)
    ax.grid(True, axis="y", alpha=0.3)
fig.suptitle("Teste passivo de 100 passos no ANYmal: erro médio em relação ao solver analítico (menor é melhor)")
fig.tight_layout()
fig.savefig(RES / "comparacao_passivo_anymal.png", dpi=130)

for (name, _, _), v in zip(models, values):
    print(name.replace("\n", " "), "->", [round(x, 3) for x in v])
