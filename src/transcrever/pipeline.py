import shutil
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from transcrever.audio import discover_audio_files, extract_audio
from transcrever.config import DEFAULT_FORMAT, DEFAULT_MODEL
from transcrever.formatters.txt import format_plain, format_raw, format_txt
from transcrever.models import Transcript
from transcrever.transcriber import transcribe

console = Console()

FORMATTERS = {
    "txt": format_txt,
}


def _output_path(source: Path, fmt: str) -> Path:
    """Gera o caminho de saída na mesma pasta do arquivo original."""
    return source.with_suffix(f".{fmt}")


def process_file(
    input_path: Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,
    device: str = "auto",
    fmt: str = DEFAULT_FORMAT,
    diarize_enabled: bool = False,
    diarize_backend: str = "speechbrain",
    hf_token: str | None = None,
    num_speakers: int | None = None,
) -> Transcript:
    """Processa um único arquivo: extrai áudio, transcreve, diariza e salva resultado."""
    formatter = FORMATTERS.get(fmt)
    if not formatter:
        raise ValueError(f"Formato não suportado: {fmt}. Use: {', '.join(FORMATTERS)}")

    # Extrai áudio para WAV temporário
    wav_path = extract_audio(input_path)

    try:
        transcript = transcribe(
            audio_path=wav_path,
            model_size=model_size,
            language=language,
            device=device,
        )
        # Atualiza source para o arquivo original
        transcript.source = str(input_path)

        # Diarização (identificação de falantes)
        if diarize_enabled:
            from transcrever.diarizer import assign_speakers, diarize

            turns = diarize(
                wav_path,
                backend=diarize_backend,
                hf_token=hf_token,
                device=device,
                num_speakers=num_speakers,
            )
            seg_dicts = [s.model_dump() for s in transcript.segments]
            seg_dicts = assign_speakers(seg_dicts, turns)
            transcript.segments = [
                transcript.segments[i].model_copy(update={"speaker": d.get("speaker")})
                for i, d in enumerate(seg_dicts)
            ]

        # Formata e salva (timestamped)
        output = formatter(transcript)
        out_path = _output_path(input_path, fmt)
        out_path.write_text(output, encoding="utf-8")

        # Salva versão texto corrido (com falantes)
        plain_output = format_plain(transcript)
        plain_path = input_path.with_stem(f"{input_path.stem}_texto").with_suffix(f".{fmt}")
        plain_path.write_text(plain_output, encoding="utf-8")

        # Salva versão texto puro (sem timestamps nem falantes)
        raw_output = format_raw(transcript)
        raw_path = input_path.with_stem(f"{input_path.stem}_puro").with_suffix(f".{fmt}")
        raw_path.write_text(raw_output, encoding="utf-8")

        console.print(f"  [green]✓[/green] {out_path.name} + {plain_path.name} + {raw_path.name}")
        return transcript
    finally:
        # Limpa o WAV temporário
        if wav_path.exists():
            wav_path.unlink()
        tmp_dir = wav_path.parent
        if tmp_dir.name.startswith("transcrever_"):
            shutil.rmtree(tmp_dir, ignore_errors=True)


def process_path(
    path: Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,
    device: str = "auto",
    fmt: str = DEFAULT_FORMAT,
    diarize_enabled: bool = False,
    diarize_backend: str = "speechbrain",
    hf_token: str | None = None,
    num_speakers: int | None = None,
) -> list[Transcript]:
    """Processa um arquivo ou diretório inteiro."""
    files = discover_audio_files(path)

    if not files:
        console.print(f"[yellow]Nenhum arquivo de áudio encontrado em {path}[/yellow]")
        return []

    console.print(f"Encontrados [bold]{len(files)}[/bold] arquivo(s) de áudio\n")

    transcripts: list[Transcript] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Transcrevendo...", total=len(files))

        for file in files:
            progress.update(task, description=f"[cyan]{file.name}[/cyan]")
            try:
                transcript = process_file(
                    input_path=file,
                    model_size=model_size,
                    language=language,
                    device=device,
                    fmt=fmt,
                    diarize_enabled=diarize_enabled,
                    diarize_backend=diarize_backend,
                    hf_token=hf_token,
                    num_speakers=num_speakers,
                )
                transcripts.append(transcript)
            except Exception as e:
                console.print(f"  [red]✗[/red] {file.name}: {e}")
            progress.advance(task)

    # Resumo
    console.print(f"\n[bold green]{len(transcripts)}/{len(files)}[/bold green] arquivo(s) transcritos")

    return transcripts
