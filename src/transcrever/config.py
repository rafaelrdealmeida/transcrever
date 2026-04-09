import shutil

AUDIO_EXTENSIONS = {
    ".m4a",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".wma",
    ".aac",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".webm",
    ".avi",
    ".mov",
}

SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

DEFAULT_MODEL = "medium"
DEFAULT_FORMAT = "txt"


def detect_device(requested: str = "auto") -> tuple[str, str]:
    """Detecta o melhor device disponível. Retorna (device, compute_type)."""
    if requested == "cuda":
        return ("cuda", "float16")
    if requested == "cpu":
        return ("cpu", "int8")

    # auto
    try:
        import ctranslate2  # noqa: F811

        if ctranslate2.get_cuda_device_count() > 0:
            return ("cuda", "float16")
    except Exception:
        pass
    return ("cpu", "int8")


def check_ffmpeg() -> bool:
    """Verifica se o ffmpeg está instalado."""
    return shutil.which("ffmpeg") is not None
