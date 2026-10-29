"""Monta vídeos lado a lado (solver analítico x solver neural NeRD) a partir dos GIFs gravados pelo NeRD.

Para cada robô, junta o GIF gravado com --env-mode ground-truth (esquerda) e o gravado com
--env-mode neural (direita), adiciona uma faixa com o nome de cada solver e salva em MP4.
No fim, concatena todos em videos/nerd_comparacao.mp4.

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

# (nome do arquivo de saída, título, pasta dos GIFs, prefixo dos GIFs)
CLIPS = [
    ("cartpole", "Cartpole: movimento passivo", "eval/eval_passive/gifs", "cartpole"),
    ("pendulum", "Pêndulo duplo com contato: movimento passivo", "eval/eval_passive/gifs", "pendulum"),
    ("anymal_walk", "ANYmal: mesma política de caminhada (RL)", "eval/eval_rl/gifs", "anymal_walk"),
]
LABELS = ("Solver analítico (Warp Sim)", "Solver neural (NeRD)")
PANEL_W, PANEL_H = 800, 600  # cada lado do vídeo
BANNER_H = 90


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT, LABEL_FONT = load_font(30), load_font(26)


def read_gif(path: Path) -> tuple[list[np.ndarray], float]:
    reader = imageio.get_reader(path)
    duration_ms = reader.get_meta_data().get("duration", 20) or 20
    frames = [np.asarray(Image.fromarray(f).convert("RGB").resize((PANEL_W, PANEL_H))) for f in reader]
    return frames, 1000.0 / duration_ms


def banner(title: str) -> np.ndarray:
    img = Image.new("RGB", (2 * PANEL_W, BANNER_H), (25, 30, 40))
    draw = ImageDraw.Draw(img)
    draw.text((PANEL_W, 26), title, font=TITLE_FONT, fill=(255, 255, 255), anchor="mm")
    for i, (label, color) in enumerate(zip(LABELS, ((120, 200, 255), (255, 190, 90)))):
        draw.text((PANEL_W // 2 + i * PANEL_W, 66), label, font=LABEL_FONT, fill=color, anchor="mm")
    return np.asarray(img)


def compose(name: str, title: str, gif_dir: str, prefix: str) -> tuple[list[np.ndarray], float]:
    left, fps = read_gif(NERD_DIR / gif_dir / f"{prefix}_ground-truth.gif")
    right, _ = read_gif(NERD_DIR / gif_dir / f"{prefix}_neural.gif")
    top = banner(title)
    n = min(len(left), len(right))
    frames = [np.vstack([top, np.hstack([left[i], right[i]])]) for i in range(n)]
    imageio.mimwrite(OUT_DIR / f"{name}.mp4", frames, fps=fps, codec="libx264", quality=8, macro_block_size=1)
    print(f"[make_videos] {name}.mp4: {n} quadros a {fps:.0f} fps ({n / fps:.1f} s)", flush=True)
    return frames, fps


OUT_DIR.mkdir(exist_ok=True)
all_frames, out_fps = [], None
for clip in CLIPS:
    frames, fps = compose(*clip)
    out_fps = out_fps or fps
    all_frames += frames
imageio.mimwrite(OUT_DIR / "nerd_comparacao.mp4", all_frames, fps=out_fps, codec="libx264", quality=8, macro_block_size=1)
print(f"[make_videos] nerd_comparacao.mp4: {len(all_frames)} quadros ({len(all_frames) / out_fps:.1f} s)", flush=True)
