# Simulação do Spot no Isaac Sim

Simulação simples do Boston Dynamics Spot (`Isaac/Robots/BostonDynamics/spot/spot.usd`) no Isaac Sim 5.0.
O robô é colocado num plano de chão e caminha usando a política de locomoção treinada por RL
(`SpotFlatTerrainPolicy`), que já vem com o Isaac Sim.

## Requisitos

- Isaac Sim 5.0 instalado via pip no ambiente conda `C:\isaac-env`
- Acesso à internet: o USD do Spot e a política são baixados do servidor de assets da NVIDIA

## Como executar

```powershell
conda activate C:\isaac-env
python spot_simulation\spot_sim.py
```

Ou simplesmente `spot_simulation\run_spot.bat`, que já usa o Python do ambiente.

| Opção | Descrição |
|---|---|
| *(nenhuma)* | Sequência automática em loop: parado → frente → giro → frente → lateral → giro |
| `--keyboard` | Controle manual pelo teclado |
| `--no-policy` | Apenas carrega o USD, sem controlador (o robô cai por gravidade) |
| `--headless` | Executa sem interface gráfica |
| `--duration N` | Encerra após N segundos simulados e imprime a posição final |

### Teclas (com `--keyboard`)

| Tecla | Ação |
|---|---|
| ↑ / ↓ (ou Numpad 8 / 2) | Andar para frente / trás |
| ← / → (ou Numpad 4 / 6) | Andar de lado |
| N / M (ou Numpad 7 / 9) | Girar à esquerda / direita |

Clique na janela do viewport antes de usar o teclado.

## Detalhes

- Física a 500 Hz; a política roda a 50 Hz (decimação 10), igual ao treinamento.
- O comando enviado à política é `[v_x, v_y, w_z]` (m/s, m/s, rad/s). Para mudar a
  sequência automática, edite `SCRIPTED_COMMANDS` em `spot_sim.py`.
- Se você parar e der play pela interface, a simulação é reiniciada.
