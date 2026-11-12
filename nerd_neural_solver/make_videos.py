"""Monta vídeos lado a lado comparando solvers, a partir dos GIFs gravados pelo NeRD.

Cada vídeo junta 2 ou mais GIFs gravados dos mesmos estados iniciais (ex.: --env-mode ground-truth
e --env-mode neural), adiciona uma faixa com o nome de cada painel e salva em MP4. Vídeos cujos GIFs
ainda não foram gravados são pulados. No fim, os vídeos marcados para o resumo são concatenados em
videos/nerd_comparacao.mp4.

Uso:
    python make_videos.py
"""

import os
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

NERD_DIR = Path(os.environ.get("NERD_DIR", r"C:\nerd"))
OUT_DIR = Path(__file__).resolve().parent / "videos"

PASSIVE, RL = "eval/eval_passive/gifs", "eval/eval_rl/gifs"
ANALYTICAL = ("Solver analítico (Warp Sim)", (120, 200, 255))
NERD = ("Solver neural (NeRD)", (255, 190, 90))

# (arquivo de saída, título, painéis [(GIF relativo ao repositório do NeRD, (rótulo, cor))], entra no resumo?)
CLIPS = [
    ("cartpole", "Cartpole: movimento passivo",
     [(f"{PASSIVE}/cartpole_ground-truth.gif", ANALYTICAL), (f"{PASSIVE}/cartpole_neural.gif", NERD)], True),
    ("pendulum", "Pêndulo duplo com contato: movimento passivo",
     [(f"{PASSIVE}/pendulum_ground-truth.gif", ANALYTICAL), (f"{PASSIVE}/pendulum_neural.gif", NERD)], True),
    ("anymal_walk", "ANYmal: mesma política de caminhada (RL)",
     [(f"{RL}/anymal_walk_ground-truth.gif", ANALYTICAL), (f"{RL}/anymal_walk_neural.gif", NERD)], True),
    ("cartpole_treino_curto", "Cartpole: modelo dos autores x nosso treino curto",
     [(f"{PASSIVE}/cartpole_ground-truth.gif", ("Analítico (Warp Sim)", ANALYTICAL[1])),
      (f"{PASSIVE}/cartpole_neural.gif", ("NeRD: 5 milhões de iterações", NERD[1])),
      (f"{PASSIVE}/cartpole_treino_curto.gif", ("NeRD: 5.600 iterações", (255, 120, 120)))], False),
    ("cartpole_treinos", "Cartpole: efeito do tempo de treino do NeRD",
     [(f"{PASSIVE}/cartpole_ground-truth.gif", ("Analítico", ANALYTICAL[1])),
      (f"{PASSIVE}/cartpole_neural.gif", ("NeRD: 5 milhões", NERD[1])),
      (f"{PASSIVE}/cartpole_treino_3h.gif", ("NeRD: 240 mil", (150, 230, 130))),
      (f"{PASSIVE}/cartpole_treino_curto.gif", ("NeRD: 5.600", (255, 120, 120)))], False),
    ("anymal_walk_treino_curto", "ANYmal: política de caminhada, modelo dos autores x nosso treino curto",
     [(f"{RL}/anymal_walk_ground-truth.gif", ("Analítico (Warp Sim)", ANALYTICAL[1])),
      (f"{RL}/anymal_walk_neural.gif", ("NeRD: 5 milhões de iterações", NERD[1])),
      (f"{RL}/anymal_walk_treino_curto.gif", ("NeRD: 5.600 iterações", (255, 120, 120)))], False),
    ("anymal_walk_treinos", "ANYmal: política de caminhada e tempo de treino do NeRD",
     [(f"{RL}/anymal_walk_ground-truth.gif", ("Analítico", ANALYTICAL[1])),
      (f"{RL}/anymal_walk_neural.gif", ("NeRD: 5 milhões", NERD[1])),
      (f"{RL}/anymal_walk_treino_240k.gif", ("NeRD: 240 mil", (150, 230, 130))),
      (f"{RL}/anymal_walk_treino_curto.gif", ("NeRD: 5.600", (255, 120, 120)))], False),
]
VIDEO_W = 1600  # largura total; cada painel tem largura VIDEO_W / número de painéis, em 4:3
BANNER_H = 90


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT, LABEL_FONT = load_font(30), load_font(24)


def read_gif(path: Path, size: tuple[int, int]) -> tuple[list[np.ndarray], float]:
    reader = imageio.get_reader(path)
    duration_ms = reader.get_meta_data().get("duration", 20) or 20
    frames = [np.asarray(Image.fromarray(f).convert("RGB").resize(size)) for f in reader]
    return frames, 1000.0 / duration_ms


def banner(title: str, labels: list[tuple[str, tuple]], panel_w: int) -> np.ndarray:
    width = panel_w * len(labels)
    img = Image.new("RGB", (width, BANNER_H), (25, 30, 40))
    draw = ImageDraw.Draw(img)
    draw.text((width // 2, 26), title, font=TITLE_FONT, fill=(255, 255, 255), anchor="mm")
    for i, (label, color) in enumerate(labels):
        draw.text((panel_w // 2 + i * panel_w, 66), label, font=LABEL_FONT, fill=color, anchor="mm")
    return np.asarray(img)


def compose(name: str, title: str, panels: list) -> tuple[list[np.ndarray], float] | None:
    missing = [gif for gif, _ in panels if not (NERD_DIR / gif).exists()]
    if missing:
        print(f"[make_videos] {name}.mp4 pulado: faltam {missing}", flush=True)
        return None
    panel_w = (VIDEO_W // len(panels)) // 2 * 2  # par, exigido pelo codificador H.264
    panel_h = panel_w * 3 // 4 // 2 * 2
    clips, fps = [], None
    for gif, _ in panels:
        frames, gif_fps = read_gif(NERD_DIR / gif, (panel_w, panel_h))
        clips.append(frames)
        fps = fps or gif_fps
    top = banner(title, [label for _, label in panels], panel_w)
    # Episódios que terminam antes (ex.: o robô caiu) ficam parados no último quadro
    n = max(len(c) for c in clips)
    frames = [np.vstack([top, np.hstack([c[min(i, len(c) - 1)] for c in clips])]) for i in range(n)]
    imageio.mimwrite(OUT_DIR / f"{name}.mp4", frames, fps=fps, codec="libx264", quality=8, macro_block_size=1)
    print(f"[make_videos] {name}.mp4: {n} quadros a {fps:.0f} fps ({n / fps:.1f} s)", flush=True)
    return frames, fps


OUT_DIR.mkdir(exist_ok=True)
summary_frames, summary_fps, summary_complete = [], None, True
for name, title, panels, in_summary in CLIPS:
    result = compose(name, title, panels)
    if in_summary:
        if result is None:
            summary_complete = False
            continue
        summary_frames += result[0]
        summary_fps = summary_fps or result[1]
# Só regrava o resumo se todos os vídeos dele foram montados; senão, um resumo antigo e completo seria perdido
if not summary_complete:
    print("[make_videos] nerd_comparacao.mp4 mantido: falta algum vídeo do resumo", flush=True)
elif summary_frames:
    imageio.mimwrite(OUT_DIR / "nerd_comparacao.mp4", summary_frames, fps=summary_fps,
                     codec="libx264", quality=8, macro_block_size=1)
    print(f"[make_videos] nerd_comparacao.mp4: {len(summary_frames)} quadros "
          f"({len(summary_frames) / summary_fps:.1f} s)", flush=True)
