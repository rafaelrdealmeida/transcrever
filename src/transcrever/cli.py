import os
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

from transcrever.config import DEFAULT_FORMAT, DEFAULT_MODEL, check_ffmpeg
from transcrever.pipeline import process_path

app = typer.Typer(
    name="transcrever",
    help="CLI para transcrição automatizada de áudio/vídeo com identificação de falantes.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def transcribe(
    path: Annotated[
        Path,
        typer.Argument(
            help="Arquivo de áudio/vídeo ou diretório para transcrever",
            exists=True,
        ),
    ],
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Modelo Whisper: tiny, base, small, medium, large-v3"),
    ] = DEFAULT_MODEL,
    language: Annotated[
        str | None,
        typer.Option("--language", "-l", help="Código do idioma (ex: pt, es, en). Auto-detecta se omitido"),
    ] = None,
    device: Annotated[
        str,
        typer.Option("--device", "-d", help="Device: auto, cpu, cuda"),
    ] = "auto",
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Formato de saída: txt"),
    ] = DEFAULT_FORMAT,
    diarize: Annotated[
        bool,
        typer.Option("--diarize", help="Ativar identificação de falantes"),
    ] = False,
    diarize_backend: Annotated[
        str,
        typer.Option("--diarize-backend", help="Backend: speechbrain (CPU, rápido) ou pyannote (GPU)"),
    ] = "speechbrain",
    hf_token: Annotated[
        str | None,
        typer.Option("--hf-token", help="Token HuggingFace para pyannote (ou use HF_TOKEN env var)"),
    ] = None,
    num_speakers: Annotated[
        int | None,
        typer.Option("--num-speakers", "-n", help="Número de falantes (ajuda a diarização)"),
    ] = None,
) -> None:
    """Transcreve arquivos de áudio/vídeo e salva resultado na mesma pasta."""
    if not check_ffmpeg():
        console.print("[red]Erro: ffmpeg não encontrado. Instale com:[/red]")
        console.print("  sudo apt install ffmpeg")
        raise typer.Exit(1)

    # Resolve HF token para backend pyannote
    if diarize and diarize_backend == "pyannote" and not hf_token:
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            console.print("[red]Erro: --hf-token ou HF_TOKEN é obrigatório para pyannote[/red]")
            raise typer.Exit(1)

    process_path(
        path=path,
        model_size=model,
        language=language,
        device=device,
        fmt=fmt,
        diarize_enabled=diarize,
        diarize_backend=diarize_backend,
        hf_token=hf_token,
        num_speakers=num_speakers,
    )
