#!/usr/bin/env python3
"""
Pipeline autonomo de transcricao via Vast.ai GPU.

Provisiona GPU -> instala ambiente -> transfere audios -> transcreve com
diarizacao (pyannote + Whisper large-v3) -> baixa resultados -> destroi instancia.

Para cada audio em arquivos/, gera na mesma pasta:
  - <nome>.txt         => com diarizacao e marcacao temporal
  - <nome>_texto.txt   => texto corrido agrupado por falante
  - <nome>_puro.txt    => texto puro, sem falantes nem timestamps

Pre-requisitos:
  1. uv sync --extra vastai
  2. VASTAI_API_KEY configurado em .env (obtenha em https://cloud.vast.ai/account/)
  3. Chave SSH (~/.ssh/id_rsa ou id_ed25519) registrada em https://cloud.vast.ai/account/
  4. HF_TOKEN configurado em .env
  5. Aceitar modelo pyannote: https://huggingface.co/pyannote/speaker-diarization-3.1

Uso:
  python scripts/vastai_transcribe.py
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ─── Caminhos fixos ────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
REMOTE = "/workspace/transcrever"

# SSH - keepalive para sessoes longas
SSH_OPTS = (
    "-o StrictHostKeyChecking=no "
    "-o UserKnownHostsFile=/dev/null "
    "-o ServerAliveInterval=30 "
    "-o ServerAliveCountMax=10 "
    "-o ConnectTimeout=15 "
    "-o LogLevel=ERROR"
)


def load_config() -> dict[str, str | int]:
    """Carrega configuracao do .env com defaults sensiveis."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    return {
        "hf_token": os.environ.get("HF_TOKEN", ""),
        "vastai_api_key": os.environ.get("VASTAI_API_KEY", ""),
        "image": os.environ.get(
            "VASTAI_IMAGE", "pytorch/pytorch:2.4.1-cuda12.4-cudnn9-runtime"
        ),
        "disk_gb": int(os.environ.get("VASTAI_DISK_GB", "40")),
        "gpu_query": os.environ.get(
            "VASTAI_GPU_QUERY",
            "num_gpus=1 gpu_ram>=12 cuda_max_good>=12.0 "
            "inet_down>100 dph_total<0.60",
        ),
        "whisper_model": os.environ.get("WHISPER_MODEL", "large-v3"),
        "num_speakers": int(os.environ.get("NUM_SPEAKERS", "2")),
        "audio_path": os.environ.get("AUDIO_PATH", "./arquivos"),
    }

# Extensoes de midia suportadas (audio + video)
MEDIA_EXTS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".wma", ".aac",
              ".mp4", ".mkv", ".webm", ".avi", ".mov"}

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov"}


# ─── Funcoes auxiliares ────────────────────────────────────────────────


def log(msg: str) -> None:
    print(f"\n>>> {msg}", flush=True)


_VASTAI_API_KEY: str = ""


def vastai_cmd(args: str) -> str:
    """Executa comando vastai CLI e retorna stdout."""
    api_flag = f"--api-key {_VASTAI_API_KEY} " if _VASTAI_API_KEY else ""
    r = subprocess.run(
        f"vastai {api_flag}{args}",
        shell=True,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"vastai {args}\n{r.stderr.strip()}")
    return r.stdout.strip()


def ssh_exec(
    host: str, port: int, script: str, *, timeout: int = 3600
) -> int:
    """Executa script bash via SSH (pipe stdin), mostrando saida em tempo real."""
    r = subprocess.run(
        f"ssh {SSH_OPTS} -p {port} root@{host} bash -s",
        shell=True,
        input=script,
        text=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
        timeout=timeout,
    )
    return r.returncode


def rsync_exec(args: str) -> None:
    """Executa rsync com verificacao de erro."""
    r = subprocess.run(f"rsync {args}", shell=True)
    if r.returncode != 0:
        raise RuntimeError(f"rsync falhou (exit {r.returncode})")


def preconvert_videos(directory: Path) -> list[Path]:
    """Converte arquivos de video para FLAC localmente antes do upload.

    Usa qualidade maxima (lossless): copia o stream de audio sem resampling.
    Retorna lista dos FLACs criados para limpeza posterior.
    """
    created: list[Path] = []
    for p in sorted(directory.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in VIDEO_EXTS:
            continue
        flac_path = p.with_suffix(".flac")
        if flac_path.exists():
            print(f"  (ja existe) {flac_path.name}", flush=True)
            created.append(flac_path)
            continue
        print(f"  {p.name} -> {flac_path.name}", flush=True)
        r = subprocess.run(
            [
                "ffmpeg", "-i", str(p),
                "-vn",           # sem video
                "-acodec", "flac",
                "-compression_level", "8",  # maximo: lossless, menor arquivo
                "-y",
                str(flac_path),
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"Falha ao converter {p.name}: {r.stderr.strip()}")
        created.append(flac_path)
    return created


def count_media_files(directory: Path) -> int:
    """Conta arquivos de audio e video na pasta."""
    count = 0
    for p in directory.rglob("*"):
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS:
            count += 1
    return count


# ─── Etapas do pipeline ───────────────────────────────────────────────


def find_gpu(gpu_query: str) -> dict:
    """Busca a GPU mais barata que atende os requisitos."""
    raw = vastai_cmd(f'search offers "{gpu_query}" -o dph_total --raw')
    offers = json.loads(raw)
    if not offers:
        raise RuntimeError(
            "Nenhuma GPU disponivel com os criterios atuais.\n"
            "Tente ajustar VASTAI_GPU_QUERY no .env (ex: aumentar dph_total ou reduzir gpu_ram)."
        )
    return offers[0]


def create_instance(offer_id: int, image: str, disk_gb: int) -> int:
    """Cria instancia Vast.ai e retorna o ID."""
    raw = vastai_cmd(
        f"create instance {offer_id} "
        f"--image {image} "
        f"--disk {disk_gb}"
    )
    # Output format: "Started. {'success': True, 'new_contract': 123, ...}"
    match = re.search(r"\{.*\}", raw)
    if not match:
        raise RuntimeError(f"Resposta inesperada ao criar instancia: {raw}")
    data = ast.literal_eval(match.group())
    if not data.get("success"):
        raise RuntimeError(f"Falha ao criar instancia: {data}")
    return data["new_contract"]


def wait_for_ssh(instance_id: int, timeout: int = 1200) -> tuple[str, int]:
    """Aguarda instancia ficar pronta com SSH acessivel."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        raw = vastai_cmd(f"show instance {instance_id} --raw")
        info = json.loads(raw)
        status = info.get("actual_status", "unknown")

        if status == "running":
            host = info.get("ssh_host")
            port = info.get("ssh_port")
            if host and port:
                test = subprocess.run(
                    f"ssh {SSH_OPTS} -p {port} root@{host} echo ok",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if test.returncode == 0:
                    return host, int(port)

        elapsed = int(time.time() - t0)
        print(f"  status: {status} ({elapsed}s)...", flush=True)
        time.sleep(15)

    raise RuntimeError(f"Timeout ({timeout}s) aguardando instancia ficar pronta")


def setup_remote(host: str, port: int) -> None:
    """Instala dependencias no servidor remoto."""
    rc = ssh_exec(
        host,
        port,
        """\
set -e
echo ">>> Instalando pacotes do sistema..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg rsync > /dev/null 2>&1

echo ">>> Instalando dependencias Python..."
# Pina torch na faixa compativel com o driver CUDA do Docker image
TORCH_MAJOR=$(python -c "import torch; v=torch.__version__.split('.'); print(f'{v[0]}.{v[1]}')")
echo "    torch pre-instalado: $(python -c 'import torch; print(torch.__version__)')"
echo "    pinando torch ~=${TORCH_MAJOR}"
pip install --quiet --no-warn-script-location \
    "torch>=${TORCH_MAJOR},<$(python -c "import torch; v=torch.__version__.split('.'); print(f'{v[0]}.{int(v[1])+1}')")" \
    'huggingface_hub>=0.20,<0.24' \
    'faster-whisper>=1.1.0' \
    'pyannote.audio>=3.1' \
    'typer>=0.15' \
    'rich>=13.0' \
    'pydantic>=2.0' \
    'python-dotenv>=1.2.2' \
    'soundfile>=0.13.1' \
    'simple-diarizer>=0.0.13'

echo ">>> Setup concluido"
""",
        timeout=900,
    )
    if rc != 0:
        raise RuntimeError("Setup remoto falhou")


def upload_project(host: str, port: int) -> None:
    """Transfere codigo-fonte e audios para o servidor.

    Videos sao excluidos: ja foram pre-convertidos para FLAC localmente.
    """
    excludes = [
        ".venv/",
        "pretrained_models/",
        "__pycache__/",
        ".git/",
        "notebooks/",
        "*.jpg",
        "*.pdf",
        "*.zip",
        "*.pyc",
        "arquivos (2)/",
        "arquivos (3)/",
        "resultados.zip",
        # Videos excluidos: FLAC pre-convertido e enviado no lugar
        "*.mp4",
        "*.mkv",
        "*.webm",
        "*.avi",
        "*.mov",
    ]
    exc_args = " ".join(f"--exclude='{e}'" for e in excludes)

    rsync_exec(
        f"-av --progress {exc_args} "
        f'-e "ssh {SSH_OPTS} -p {port}" '
        f'"{ROOT}/" root@{host}:"{REMOTE}/"'
    )


def run_transcription(
    host: str,
    port: int,
    hf_token: str,
    whisper_model: str,
    num_speakers: int,
    audio_path: str,
) -> None:
    """Instala o projeto e executa a transcricao no servidor."""
    rc = ssh_exec(
        host,
        port,
        f"""\
set -e
cd {REMOTE}

echo ">>> Instalando projeto..."
pip install -e . --quiet --no-deps --no-warn-script-location

echo ">>> Iniciando transcricao..."
export HF_TOKEN="{hf_token}"
transcrever '{audio_path}' \
    --model {whisper_model} \
    --diarize \
    --diarize-backend pyannote \
    --device cuda \
    --num-speakers {num_speakers}

echo ">>> Transcricao concluida"
""",
        timeout=21600,  # 6 horas
    )
    if rc != 0:
        print(
            "AVISO: Transcricao pode ter falhado parcialmente. "
            "Resultados parciais serao baixados.",
            flush=True,
        )


def download_results(host: str, port: int) -> None:
    """Baixa apenas os arquivos .txt gerados pela transcricao."""
    rsync_exec(
        "-av --progress "
        "--include='*/' --include='*.txt' --exclude='*' "
        f'-e "ssh {SSH_OPTS} -p {port}" '
        f'root@{host}:"{REMOTE}/arquivos/" "{ROOT}/arquivos/"'
    )


def destroy_instance(instance_id: int) -> None:
    """Destroi a instancia Vast.ai."""
    try:
        api_flag = f"--api-key {_VASTAI_API_KEY} " if _VASTAI_API_KEY else ""
        subprocess.run(
            f"echo y | vastai {api_flag}destroy instance {instance_id}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        print(
            f"AVISO: Falha ao destruir instancia #{instance_id}. "
            f"Destrua manualmente: vastai destroy instance {instance_id}",
            flush=True,
        )


# ─── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    global _VASTAI_API_KEY

    cfg = load_config()
    _VASTAI_API_KEY = cfg["vastai_api_key"]

    # --- Validacoes ---
    hf_token = cfg["hf_token"]
    if not hf_token:
        sys.exit(
            "ERRO: HF_TOKEN nao encontrado.\n"
            "Configure em .env (veja .env.example para instrucoes)"
        )

    if not shutil.which("vastai"):
        sys.exit(
            "ERRO: CLI vastai nao encontrado.\n"
            "Instale com: pip install vastai\n"
            "Configure com: vastai set api-key SUA_CHAVE"
        )

    audio_path = cfg["audio_path"]
    arquivos_dir = ROOT / audio_path.lstrip("./")
    if not arquivos_dir.exists():
        sys.exit(f"ERRO: Pasta '{arquivos_dir}' nao encontrada")

    n_media = count_media_files(arquivos_dir)
    if n_media == 0:
        sys.exit(f"ERRO: Nenhum arquivo de midia encontrado em '{arquivos_dir}'")

    whisper_model = cfg["whisper_model"]
    num_speakers = cfg["num_speakers"]

    # --- Pipeline ---
    print("=" * 58)
    print("  Pipeline Vast.ai - Transcricao com Diarizacao")
    print(f"  {n_media} arquivo(s) de midia | Modelo: {whisper_model}")
    print("=" * 58)

    # 1. GPU
    log("1/7 - Buscando GPU disponivel...")
    offer = find_gpu(cfg["gpu_query"])
    gpu_name = offer.get("gpu_name", "GPU")
    dph = offer.get("dph_total", 0)
    print(f"  {gpu_name} - ${dph:.3f}/hora")

    # 2. Instancia
    log("2/7 - Criando instancia...")
    instance_id = create_instance(offer["id"], cfg["image"], cfg["disk_gb"])
    print(f"  Instancia #{instance_id} criada")

    # Pre-conversao de videos para FLAC (lossless, muito menor que MP4)
    log("2.5/7 - Convertendo videos para FLAC...")
    converted_flacs = preconvert_videos(arquivos_dir)
    if converted_flacs:
        print(f"  {len(converted_flacs)} video(s) convertido(s) para FLAC")
    else:
        print("  Nenhum video encontrado para converter")

    t_start = time.time()

    try:
        # 3. SSH
        log("3/7 - Aguardando instancia (2-5 min)...")
        host, port = wait_for_ssh(instance_id)
        print(f"  SSH pronto: {host}:{port}")

        # 4. Setup
        log("4/7 - Instalando dependencias no servidor...")
        setup_remote(host, port)
        print("  Dependencias instaladas")

        # 5. Upload
        log("5/7 - Transferindo projeto + audios...")
        upload_project(host, port)
        print("  Upload concluido")

        # 6. Transcricao
        log("6/7 - Transcrevendo (pode levar horas)...")
        run_transcription(host, port, hf_token, whisper_model, num_speakers, audio_path)

        # 7. Download
        log("7/7 - Baixando resultados...")
        download_results(host, port)
        print("  Resultados baixados")

    finally:
        log("Destruindo instancia...")
        destroy_instance(instance_id)
        print("  Instancia destruida")

        # Remove FLACs temporarios gerados pela pre-conversao
        for flac in converted_flacs:
            try:
                flac.unlink()
            except OSError:
                pass

    elapsed = time.time() - t_start
    cost = (elapsed / 3600) * dph
    mins = int(elapsed // 60)

    print()
    print("=" * 58)
    print(f"  Concluido em {mins} min - custo estimado: ${cost:.2f}")
    print(f"  Resultados em: {arquivos_dir}/")
    print("=" * 58)
    print()
    print("Cada pasta de entrevista agora contem:")
    print("  <nome>.txt       -> diarizacao + marcacao temporal")
    print("  <nome>_texto.txt -> texto corrido por falante")
    print("  <nome>_puro.txt  -> texto puro (sem falantes/timestamps)")


if __name__ == "__main__":
    main()
