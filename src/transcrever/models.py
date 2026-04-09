from pydantic import BaseModel


class Segment(BaseModel):
    """Um trecho de transcrição com timestamps."""

    start: float
    end: float
    text: str
    speaker: str | None = None
    language: str | None = None


class Transcript(BaseModel):
    """Transcrição completa de um arquivo de áudio."""

    source: str
    language: str
    segments: list[Segment]
    metadata: dict[str, str | float | int] = {}
