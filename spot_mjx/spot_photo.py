"""Coloca o Boston Dynamics Spot em cena no MuJoCo MJX (JAX, na GPU) e salva uma foto (PNG).

Roda no WSL2 (Ubuntu). Usa o modelo do Spot do MuJoCo Menagerie (scene.xml: robô + chão + luz),
baixado automaticamente na primeira execução. O MJX calcula a cinemática da pose em pé "home"
na GPU; como o MJX não tem renderizador próprio, o estado volta para a CPU e a foto sai do
renderizador do MuJoCo. A física não é executada.

Uso (dentro do WSL, com o ambiente ~/envs/mjx ativo):
    python spot_photo.py                       # salva spot_mjx.png ao lado do script
    python spot_photo.py --out foto.png --width 1920 --height 1080
"""

import argparse
import math
import os
import subprocess
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")  # renderização sem janela
# Por padrão o JAX reserva 75% da VRAM ao iniciar; aqui ele aloca só o que precisar
os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")

import jax
import mujoco
import numpy as np
from mujoco import mjx
from PIL import Image

parser = argparse.ArgumentParser(description="Foto do Spot no MuJoCo MJX")
parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spot_mjx.png"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
args = parser.parse_args()

MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"
CACHE_DIR = Path.home() / ".cache" / "mujoco_menagerie"


def download_spot() -> Path:
    """Baixa só a pasta boston_dynamics_spot do Menagerie (clone esparso)."""
    spot_dir = CACHE_DIR / "boston_dynamics_spot"
    if not (spot_dir / "scene.xml").exists():
        print(f"[spot_photo] Baixando o Spot do Menagerie em {CACHE_DIR}...", flush=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", MENAGERIE_URL, str(CACHE_DIR)], check=True
        )
        subprocess.run(["git", "-C", str(CACHE_DIR), "sparse-checkout", "set", "boston_dynamics_spot"], check=True)
    return spot_dir


spot_dir = download_spot()
model = mujoco.MjModel.from_xml_path(str(spot_dir / "scene.xml"))
data = mujoco.MjData(model)
mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)

# Modelo e estado vão para a GPU; o MJX calcula a cinemática lá
mjx_model = mjx.put_model(model)
mjx_data = jax.jit(mjx.forward)(mjx_model, mjx.put_data(model, data))
print(f"[spot_photo] Spot carregado no MJX ({jax.devices()[0]}): {model.nbody} corpos, {model.nv} DOFs", flush=True)

# Estado de volta para a CPU, só para renderizar
mjx.get_data_into(data, model, mjx_data)

model.vis.global_.offwidth = max(model.vis.global_.offwidth, args.width)
model.vis.global_.offheight = max(model.vis.global_.offheight, args.height)

# Câmera em diagonal, olhando para o centro do robô (mesmo enquadramento das fotos dos outros simuladores)
target = np.array([0.0, 0.0, 0.3])
cam_pos = np.array([1.6, -1.6, 0.9])
d = target - cam_pos
camera = mujoco.MjvCamera()
camera.type = mujoco.mjtCamera.mjCAMERA_FREE
camera.lookat[:] = target
camera.distance = float(np.linalg.norm(d))
camera.azimuth = math.degrees(math.atan2(d[1], d[0]))
camera.elevation = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))

with mujoco.Renderer(model, height=args.height, width=args.width) as renderer:
    renderer.update_scene(data, camera=camera)
    image = renderer.render()

Image.fromarray(image).save(args.out)
print(f"[spot_photo] Foto salva em {args.out}", flush=True)
