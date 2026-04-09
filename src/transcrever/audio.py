import subprocess
import tempfile
from pathlib import Path

from transcrever.config import SUPPORTED_EXTENSIONS


def discover_audio_files(root: Path) -> list[Path]:
    """Descobre arquivos de áudio/vídeo recursivamente a partir de um diretório."""
    if root.is_file():
        if root.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [root]
        return []

    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


def extract_audio(input_path: Path, output_dir: Path | None = None) -> Path:
    """Extrai/converte áudio para WAV 16kHz mono via ffmpeg.

    Se output_dir não for fornecido, usa um diretório temporário.
    Retorna o caminho do arquivo WAV gerado.
    """
    if output_dir:
        wav_path = output_dir / f"{input_path.stem}.wav"
    else:
        tmp = tempfile.mkdtemp(prefix="transcrever_")
        wav_path = Path(tmp) / f"{input_path.stem}.wav"

    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-vn",  # sem vídeo
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",  # mono
        "-y",  # sobrescrever
        str(wav_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Erro ao extrair áudio de {input_path.name}: {result.stderr.strip()}"
        )

    return wav_path
