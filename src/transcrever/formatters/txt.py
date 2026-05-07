from transcrever.models import Transcript


def _format_timestamp(seconds: float) -> str:
    """Converte segundos para formato HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_txt(transcript: Transcript) -> str:
    """Formata uma transcrição como texto com timestamps e speaker labels."""
    lines: list[str] = []

    for seg in transcript.segments:
        ts = f"[{_format_timestamp(seg.start)} - {_format_timestamp(seg.end)}]"
        speaker = f" [{seg.speaker}]" if seg.speaker else ""
        lines.append(f"{ts}{speaker} {seg.text}")

    return "\n".join(lines) + "\n"


def format_plain(transcript: Transcript) -> str:
    """Formata uma transcrição como texto corrido, sem timestamps."""
    parts: list[str] = []
    current_speaker: str | None = None

    for seg in transcript.segments:
        if seg.speaker and seg.speaker != current_speaker:
            current_speaker = seg.speaker
            parts.append(f"\n\n[{seg.speaker}]\n")

        parts.append(seg.text)

    return " ".join(parts).replace("  ", " ").strip() + "\n"


def format_turns(transcript: Transcript) -> str:
    """Formata cada segmento como uma linha separada dentro do bloco do falante.

    Turnos diferentes são separados por linha em branco.
    """
    lines: list[str] = []
    current_speaker: str | None = None

    for seg in transcript.segments:
        if seg.speaker and seg.speaker != current_speaker:
            current_speaker = seg.speaker
            if lines:
                lines.append("")
            lines.append(f"[{seg.speaker}]")

        lines.append(seg.text.strip())

    return "\n".join(lines).strip() + "\n"


def format_raw(transcript: Transcript) -> str:
    """Formata uma transcrição como texto puro, sem timestamps nem falantes."""
    texts = [seg.text for seg in transcript.segments]
    return " ".join(texts).strip() + "\n"
