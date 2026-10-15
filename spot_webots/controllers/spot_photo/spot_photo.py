"""Controlador do robô fotógrafo: espera o Spot se acomodar, salva a imagem da câmera e fecha o Webots.

Variáveis de ambiente opcionais:
    SPOT_PHOTO_OUT   caminho do PNG (padrão: spot_webots.png na raiz da pasta spot_webots)
    SPOT_PHOTO_KEEP  se "1", não fecha o Webots depois da foto
"""

import os

from controller import Supervisor

SETTLE_TIME = 2.0  # segundos simulados para o Spot se acomodar antes da foto

project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
out_path = os.environ.get("SPOT_PHOTO_OUT", os.path.join(project_dir, "spot_webots.png"))

robot = Supervisor()
time_step = int(robot.getBasicTimeStep())

camera = robot.getDevice("camera")
camera.enable(time_step)

while robot.step(time_step) != -1 and robot.getTime() < SETTLE_TIME:
    pass

camera.saveImage(out_path, 100)
print(f"[spot_photo] Foto salva em {out_path}", flush=True)

if os.environ.get("SPOT_PHOTO_KEEP") == "1":
    while robot.step(time_step) != -1:
        pass
else:
    robot.simulationQuit(0)
    robot.step(time_step)
