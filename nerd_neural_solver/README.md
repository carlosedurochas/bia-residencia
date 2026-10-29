# Solver analítico x solver neural (NeRD)

Comparação prática entre um solver de física matemático e um solver neural, usando os modelos pré-treinados do
**NeRD** (*Neural Robot Dynamics*, Xu et al., CoRL 2025; [artigo](https://arxiv.org/abs/2508.15755),
[código](https://github.com/NVlabs/neural-robot-dynamics)). Nada foi treinado aqui.

O NeRD substitui só a parte de dinâmica e contato do simulador por um Transformer treinado com dados do próprio
simulador. O resto (cena, robô, controle) continua igual, e o mesmo comando roda com um solver ou com o outro:

- `--env-mode ground-truth`: solver analítico do **Warp Sim** (equações de dinâmica de corpos rígidos com contato);
- `--env-mode neural`: o modelo NeRD prevê o próximo estado a partir do estado atual e da ação.

**Sobre o Newton:** o código principal do NeRD roda sobre o Warp Sim, o motor de física que vinha dentro do NVIDIA Warp
e foi substituído pelo **Newton**. O próprio Warp avisa: *"warp.sim is deprecated (...) Please transition to using
the forthcoming Newton library"*. A integração do NeRD como solver do Newton existe no branch
[`nerd_newton_dev`](https://github.com/NVlabs/neural-robot-dynamics/tree/nerd_newton_dev), ainda em desenvolvimento e
com só dois exemplos (Cartpole e Ant).

## Vídeos

Em [`videos/`](videos/), cada vídeo mostra o solver analítico à esquerda e o NeRD à direita, a partir dos mesmos
estados iniciais:

| Vídeo | O que mostra |
|---|---|
| [`cartpole.mp4`](videos/cartpole.mp4) | Cartpole caindo livremente (3 episódios de 200 passos) |
| [`pendulum.mp4`](videos/pendulum.mp4) | Pêndulo duplo batendo no chão (3 episódios de 200 passos) |
| [`anymal_walk.mp4`](videos/anymal_walk.mp4) | Quadrúpede ANYmal andando com a mesma política de RL (400 passos) |
| [`nerd_comparacao.mp4`](videos/nerd_comparacao.mp4) | Os três em sequência (32 s) |

## Resultados

### Movimento passivo: erro do NeRD em relação ao solver analítico

2.048 trajetórias de 100 passos, sem ação, partindo dos mesmos estados iniciais. O erro é a média ao longo de toda
a trajetória (logs em [`results/`](results/)).

| Robô | Parâmetros do NeRD | Posição da base | Orientação da base | Juntas |
|---|---|---|---|---|
| Cartpole | 2,7 M | 0,16 mm (carrinho) | — | 0,02° |
| Pêndulo duplo com contato | 2,7 M | — | 0,24° | 0,40° |
| ANYmal (quadrúpede) | 10,9 M | 4,9 mm | 0,33° | 0,32° |
| Ant (quadrúpede) | 10,9 M | 53 mm | 5,1° | 5,2° |

O erro do Ant é muito maior porque o modelo foi treinado com dados do Warp 1.5.1, e aqui a referência foi gerada
com o Warp 1.8.0. O README do NeRD avisa que as duas versões produzem movimentos diferentes; para reproduzir os números
do artigo no Ant, seria preciso o Warp 1.5.1.

### Mesma política de RL nos dois solvers

Política `forward_walk/0` do ANYmal (treinada pelos autores dentro do NeRD), 512 episódios de até 1.000 passos:

| Solver | Recompensa média | Duração média do episódio |
|---|---|---|
| Analítico (Warp Sim) | 1.329,9 | 993,4 passos |
| Neural (NeRD) | 1.327,0 | 991,3 passos |

A política treinada no simulador neural se comporta quase igual no analítico: a diferença de recompensa é de 0,2%.

## Como reproduzir

### Instalação (Windows)

```powershell
git clone https://github.com/NVlabs/neural-robot-dynamics.git C:\nerd
cd C:\nerd
git lfs pull                       # os modelos (.pt) ficam no Git LFS

conda create -y -p C:\nerd-env python=3.10
C:\nerd-env\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu128
C:\nerd-env\python.exe -m pip install -r C:\nerd\requirements.txt
C:\nerd-env\python.exe -m pip install gym imageio imageio-ffmpeg
```

Também é preciso o `ffmpeg` no PATH (o NeRD o usa para gerar os GIFs).

### Execução

```powershell
nerd_neural_solver\run_all.bat
```

Refaz as métricas, as gravações e os vídeos (cerca de 15 min). Para rodar um script do NeRD isoladamente:

```powershell
C:\nerd-env\python.exe nerd_neural_solver\nerd_run.py eval/eval_rl/run_rl.py --rl-cfg ./cfg/Anymal/anymal_forward.yaml --playback ../../pretrained_models/RL_policies/Anymal/forward_walk/0/nn/AnymalPPO.pth --num-envs 1 --num-games 1 --env-mode neural --render
```

## Arquivos

| Arquivo | Papel |
|---|---|
| [`nerd_codigo/`](nerd_codigo/) | Cópia dos arquivos do NeRD que explicam o solver neural, com guia de leitura |
| `nerd_run.py` | Lançador: roda qualquer script do NeRD com o PyTorch atual (ver abaixo) |
| `make_videos.py` | Junta os GIFs dos dois solvers em vídeos lado a lado |
| `run_all.bat` | Refaz tudo |
| `results/` | Logs das métricas |
| `videos/` | Vídeos de comparação |

## Adaptações em relação ao repositório original

O NeRD foi testado com Python 3.8 e PyTorch 2.2.2 no Ubuntu. Aqui roda no Windows com Python 3.10 e PyTorch 2.11
(CUDA 12.8), necessário para a RTX 5070 Ti. O código da NVIDIA não foi modificado; as diferenças são:

- **Carregamento dos modelos.** Os checkpoints foram salvos como objetos Python completos (`torch.save(model)`).
  A partir do PyTorch 2.6, o `torch.load` recusa isso por padrão (`weights_only=True`), porque carregar um objeto
  Python pode executar código. Em vez de desligar a proteção, o `nerd_run.py` libera só as 20 classes que os
  checkpoints usam (a arquitetura do NeRD, módulos do `torch.nn` e tipos do NumPy), listadas com
  `torch.serialization.get_unsafe_globals_in_checkpoint`.
- **Pacote `gym`:** usado pelos scripts de RL e ausente do `requirements.txt`.
- **Aviso `Warp CUDA error: Failed to get driver entry point 'cuDeviceGetUuid'`:** aparece com o Warp 1.8.0 e o
  driver atual, mas a GPU é usada normalmente.
