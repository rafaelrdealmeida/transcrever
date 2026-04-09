import time
from pathlib import Path

from faster_whisper import WhisperModel

from transcrever.config import DEFAULT_MODEL, detect_device
from transcrever.models import Segment, Transcript


def transcribe(
    audio_path: Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,
    device: str = "auto",
) -> Transcript:
    """Transcreve um arquivo de áudio usando faster-whisper."""
    dev, compute_type = detect_device(device)

    model = WhisperModel(model_size, device=dev, compute_type=compute_type)

    start_time = time.time()
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
    )

    segments: list[Segment] = []
    for seg in segments_iter:
        segments.append(
            Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                language=info.language,
            )
        )

    elapsed = time.time() - start_time

    return Transcript(
        source=str(audio_path),
        language=info.language,
        segments=segments,
        metadata={
            "model": model_size,
            "device": dev,
            "compute_type": compute_type,
            "language_probability": round(info.language_probability, 2),
            "duration": round(info.duration, 1),
            "processing_time": round(elapsed, 1),
        },
    )
