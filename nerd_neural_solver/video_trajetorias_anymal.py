"""Grava um vídeo em grade 10x10 com 100 trajetórias de exemplo do conjunto de dados do ANYmal.

Usa o mesmo gerador do conjunto de treino do NeRD (generate/generate_dataset_anymal.py): 100 ambientes
em paralelo, cada um com uma trajetória de 100 passos partindo do robô em pé, com comandos aleatórios nas
juntas, simulada pelo solver analítico (Warp Sim). O renderizador do Warp desenha cada ambiente no seu
próprio quadro ("tiled rendering"), e a tela inteira já sai como a grade. Os quadros são capturados e
salvos em MP4.

As trajetórias são estatisticamente iguais às do conjunto de dados (mesmo gerador e mesmas faixas de
sorteio), mas não são as mesmas: o sorteio depende do número de ambientes.

Uso:
    python video_trajetorias_anymal.py [--grid 10] [--tile 160] [--speed 0.5] [--seed 0]
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

NERD_DIR = os.environ.get("NERD_DIR", r"C:\nerd")
sys.path.insert(0, NERD_DIR)

import imageio.v2 as imageio
import numpy as np
import warp as wp
from PIL import Image, ImageDraw, ImageFont

from envs.neural_environment import NeuralEnvironment
from envs.warp_sim_envs.env_anymal import AnymalEnvironment
from envs.warp_sim_envs.environment import Environment
from generate.generate_dataset_anymal import collect_dataset
from utils.python_utils import set_random_seed

parser = argparse.ArgumentParser()
parser.add_argument("--grid", type=int, default=10, help="lado da grade (grid x grid trajetórias)")
parser.add_argument("--tile", type=int, default=160, help="tamanho de cada quadro em pixels")
parser.add_argument("--steps", type=int, default=100, help="passos por trajetória (como no conjunto de dados)")
parser.add_argument("--speed", type=float, default=0.25, help="velocidade de reprodução (1 = tempo real)")
parser.add_argument("--cam", type=float, nargs=3, default=[1.0, 0.6, 1.2],
                    help="posição da câmera de cada quadro (coordenadas do renderizador; o robô fica na origem)")
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "videos" / "anymal_dataset_10x10.mp4"))
args = parser.parse_args()

n_envs, side = args.grid * args.grid, args.grid * args.tile

# Renderização em quadros: um ambiente por quadro, numa grade grid x grid, sem janela visível.
# Com use_tiled_rendering, todos os robôs ficam na origem e cada quadro desenha só o seu.
AnymalEnvironment.use_tiled_rendering = True
AnymalEnvironment.opengl_render_settings = dict(
    AnymalEnvironment.opengl_render_settings, screen_width=side, screen_height=side, headless=True
)


def setup_tiled_renderer(self):
    """Igual ao Environment.setup_renderer do NeRD, mas agrupando as instâncias pelo corpo a que pertencem.

    O original supõe que as formas visíveis do ambiente i são as instâncias i*k a (i+1)*k-1, o que não vale
    para o ANYmal (KeyError no renderizador)."""
    self.use_tiled_rendering = False
    Environment.setup_renderer(self)  # cria o renderizador sem quadros
    self.use_tiled_rendering = True
    r = self.renderer
    bodies_per_env = self.model.body_count // self.num_envs
    per_env, shared = [[] for _ in range(self.num_envs)], []
    for instance, body, *_ in r._instances.values():
        if body is None or body < 0:
            shared.append(instance)  # chão
        else:
            per_env[body // bodies_per_env].append(instance)
    # Câmera em diagonal, perto do robô (a câmera padrão fica a 10 unidades e o robô quase some)
    cam_pos, target = np.array(args.cam, dtype=float), np.array([0.0, 0.12, 0.0])
    front = (target - cam_pos) / np.linalg.norm(target - cam_pos)
    view = r.compute_view_matrix(cam_pos, front, r._camera_up)
    r.setup_tiled_rendering(
        instances=[p + shared for p in per_env],
        tile_width=args.tile, tile_height=args.tile, tile_ncols=args.grid, tile_nrows=args.grid,
        view_matrices=[view] * self.num_envs,
    )


AnymalEnvironment.setup_renderer = setup_tiled_renderer

# Captura de cada quadro renderizado (substitui a exportação em GIF do NeRD)
frames = []


def capture(self):
    self.env.render()
    img = wp.zeros((self.env.renderer.screen_height, self.env.renderer.screen_width, 3), dtype=wp.uint8)
    self.env.renderer.get_pixels(img, split_up_tiles=False, mode="rgb", use_uint8=True)
    frames.append(img.numpy())
    capture.frame_dt = self.env.frame_dt


NeuralEnvironment.render = capture

set_random_seed(args.seed)
sample_path = os.path.join(tempfile.gettempdir(), "nerd_anymal_amostra_video.hdf5")  # dados descartados
collect_dataset(
    env_name="AnymalJointPositionControl",
    num_envs=n_envs,
    initial_states_source="env",
    num_transitions=n_envs * args.steps,
    trajectory_length=args.steps,
    dataset_path=sample_path,
    seed=args.seed,
    render=True,
)
try:
    os.remove(sample_path)
except OSError:
    pass

# Faixa com o título por cima da grade
fps = args.speed / capture.frame_dt
font = None
for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf"):
    try:
        font = ImageFont.truetype(name, max(14, min(30, side // 50)))
        break
    except OSError:
        pass
banner = Image.new("RGB", (side, 60), (25, 30, 40))
ImageDraw.Draw(banner).text(
    (side // 2, 30),
    f"ANYmal: {n_envs} trajetórias de exemplo do conjunto de dados (comandos aleatórios, solver analítico) · "
    f"{args.speed:g}x".replace(".", ","),
    font=font or ImageFont.load_default(), fill=(255, 255, 255), anchor="mm",
)
banner = np.asarray(banner)
video = [np.vstack([banner, f]) for f in frames]
imageio.mimwrite(args.out, video, fps=fps, codec="libx264", quality=8, macro_block_size=1)
print(f"[video] {args.out}: {len(video)} quadros, {len(video) / fps:.1f} s "
      f"(passo de {capture.frame_dt * 1000:.0f} ms, {args.speed:g}x)", flush=True)
