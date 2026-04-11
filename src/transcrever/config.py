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


def _cuda_compute_type() -> str:
    """Detecta compute type ideal para a GPU (float16 requer compute >= 7.0)."""
    # Tenta via PyTorch
    try:
        import torch

        if torch.cuda.is_available():
            major, _ = torch.cuda.get_device_capability()
            return "float16" if major >= 7 else "float32"
    except (ImportError, Exception):
        pass

    # Fallback: tenta via ctranslate2 (testa float16 diretamente)
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            # Se compute capability < 7.0, float16 vai falhar no CTranslate2
            # Tenta criar um modelo minimo para verificar
            try:
                ctranslate2.get_supported_compute_types("cuda")
                supported = ctranslate2.get_supported_compute_types("cuda")
                if "float16" in supported:
                    return "float16"
                return "float32"
            except Exception:
                pass
    except (ImportError, Exception):
        pass

    return "float32"


def detect_device(requested: str = "auto") -> tuple[str, str]:
    """Detecta o melhor device disponível. Retorna (device, compute_type)."""
    if requested == "cpu":
        return ("cpu", "int8")

    if requested == "cuda":
        return ("cuda", _cuda_compute_type())

    # auto
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return ("cuda", _cuda_compute_type())
    except Exception:
        pass
    return ("cpu", "int8")


def check_ffmpeg() -> bool:
    """Verifica se o ffmpeg está instalado."""
    return shutil.which("ffmpeg") is not None
