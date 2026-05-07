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
    """Agrupa toda a fala de cada falante, independente da ordem cronológica."""
    from collections import defaultdict

    by_speaker: dict[str, list[str]] = defaultdict(list)
    speaker_order: list[str] = []

    for seg in transcript.segments:
        speaker = seg.speaker or "?"
        if speaker not in by_speaker:
            speaker_order.append(speaker)
        by_speaker[speaker].append(seg.text.strip())

    blocks: list[str] = []
    for speaker in speaker_order:
        lines = [f"[{speaker}]"] + by_speaker[speaker]
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks).strip() + "\n"


def format_raw(transcript: Transcript) -> str:
    """Formata uma transcrição como texto puro, sem timestamps nem falantes."""
    texts = [seg.text for seg in transcript.segments]
    return " ".join(texts).strip() + "\n"
