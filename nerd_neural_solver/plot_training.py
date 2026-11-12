"""Desenha as curvas de aprendizado de um treino do NeRD a partir do log do train.py.

Lê, para cada época, a perda de treino, a perda de validação e o erro da avaliação por simulação
(rollout de 10 passos comparado ao solver analítico) e salva um gráfico PNG.

Uso:
    python plot_training.py results/treino_curto_cartpole.log results/curva_treino_cartpole.png
"""

import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

log_path, out_path = sys.argv[1], sys.argv[2]
text = open(log_path, encoding="utf-8", errors="ignore").read()
text = re.sub(r"\x1b\[[0-9;]*m", "", text)  # remove as cores do terminal

# O log de cada época traz [Evaluate] antes do cabeçalho "Epoch N"; a época 0 não tem [Train]
evals = [float(x) for x in re.findall(r"\[Evaluate\].*?Rollout MSE Error = ([0-9.eE+-]+)", text)]
trains = [float(x) for x in re.findall(r"\[Train\] loss = ([0-9.eE+-]+)", text)]
valids = [float(x) for x in re.findall(r"\[Valid\] dataset \[\w+\]: loss = ([0-9.eE+-]+)", text)]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
mk = len(evals) <= 50  # marcadores só quando há poucas épocas

ax1.plot(range(1, len(trains) + 1), trains, "o-" if mk else "-", lw=1, label="Treino")  # a época 0 só avalia, não treina
ax1.plot(range(len(valids)), valids, "s-" if mk else "-", lw=1, alpha=0.8, label="Validação")
ax1.set_title("Perda (erro quadrático normalizado)")
ax1.set_xlabel("Época (400 iterações)")
ax1.set_yscale("log")
ax1.grid(True, which="both", alpha=0.3)
ax1.legend()

ax2.plot(range(len(evals)), evals, "o-" if mk else "-", lw=1, color="tab:green")
ax2.set_title("Simulação de 10 passos x solver analítico")
ax2.set_xlabel("Época (400 iterações)")
ax2.set_ylabel("Erro quadrático médio do estado")
ax2.set_yscale("log")
ax2.grid(True, which="both", alpha=0.3)

fig.suptitle(sys.argv[3] if len(sys.argv) > 3 else "Treino do NeRD no Cartpole")
fig.tight_layout()
fig.savefig(out_path, dpi=120)
print(f"[plot_training] {len(trains)} épocas de treino, {len(valids)} validações, {len(evals)} avaliações -> {out_path}")
print(f"[plot_training] avaliação: início {evals[0]:.3g}, fim {evals[-1]:.3g}, melhor {min(evals):.3g}")
