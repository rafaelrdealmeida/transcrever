from pathlib import Path

from pydantic import BaseModel


class SpeakerTurn(BaseModel):
    """Um trecho de fala atribuído a um falante."""

    start: float
    end: float
    speaker: str


def diarize_speechbrain(
    audio_path: Path,
    num_speakers: int | None = None,
) -> list[SpeakerTurn]:
    """Identifica falantes usando simple-diarizer (SpeechBrain). Rápido em CPU."""
    import os

    import numpy as np
    import soundfile as sf
    import torch
    from simple_diarizer.cluster import cluster_SC
    from simple_diarizer.diarizer import Diarizer
    from speechbrain.inference import EncoderClassifier

    # Carrega áudio com soundfile (evita problemas com torchcodec)
    data, sample_rate = sf.read(str(audio_path))
    signal = torch.from_numpy(data).float().unsqueeze(0)  # (1, samples)

    # Carrega modelo ECAPA-TDNN localmente se disponível
    run_opts = {"device": "cpu"}
    local_model = os.path.expanduser(
        "~/.cache/huggingface/hub/speechbrain_spkrec-ecapa-voxceleb"
    )
    local_hparams = os.path.join(local_model, "hyperparams_local.yaml")
    if os.path.exists(local_hparams):
        embed_model = EncoderClassifier.from_hparams(
            source=local_model,
            hparams_file="hyperparams_local.yaml",
            run_opts=run_opts,
        )
    else:
        embed_model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=local_model,
            run_opts=run_opts,
        )

    # Extrai embeddings por janela
    window = 1.5  # segundos
    period = 0.75  # segundos
    allsegments: list[dict] = []
    embeddings = []

    duration = signal.shape[1] / sample_rate
    start = 0.0
    while start + window <= duration:
        s = int(start * sample_rate)
        e = int((start + window) * sample_rate)
        chunk = signal[:, s:e]
        with torch.no_grad():
            emb = embed_model.encode_batch(chunk).squeeze().numpy()
        embeddings.append(emb)
        allsegments.append({"start": start, "end": start + window})
        start += period

    if not embeddings:
        return []

    embeddings_arr = np.array(embeddings)

    # Clustering
    n_speakers = num_speakers or 2
    labels = cluster_SC(embeddings_arr, n_clusters=n_speakers, enhance_sim=True)

    # Atribui labels aos segmentos
    for i, seg in enumerate(allsegments):
        seg["label"] = int(labels[i])

    # Junta segmentos adjacentes do mesmo falante
    merged: list[dict] = []
    for seg in allsegments:
        if merged and merged[-1]["label"] == seg["label"]:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(dict(seg))

    turns: list[SpeakerTurn] = []
    for seg in merged:
        turns.append(
            SpeakerTurn(
                start=seg["start"],
                end=seg["end"],
                speaker=f"Falante {seg['label'] + 1}",
            )
        )

    return turns


def diarize_pyannote(
    audio_path: Path,
    hf_token: str,
    device: str = "auto",
) -> list[SpeakerTurn]:
    """Identifica falantes usando pyannote.audio. Melhor com GPU."""
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        raise RuntimeError(
            "pyannote.audio não instalado. Execute: uv sync --extra diarize"
        )

    import soundfile as sf
    import torch

    torch_device = torch.device("cuda" if device != "cpu" and torch.cuda.is_available() else "cpu")

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,
    )
    pipeline.to(torch_device)

    # Pré-carrega o áudio com soundfile para evitar dependência do torchcodec
    data, sample_rate = sf.read(str(audio_path))
    waveform = torch.from_numpy(data).float()
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    else:
        waveform = waveform.T
    audio_input = {"waveform": waveform, "sample_rate": sample_rate}

    result = pipeline(audio_input)

    # pyannote 3.1+ retorna DiarizeOutput dataclass
    diarization = getattr(result, "speaker_diarization", result)

    turns: list[SpeakerTurn] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append(
            SpeakerTurn(
                start=turn.start,
                end=turn.end,
                speaker=speaker,
            )
        )

    return turns


def diarize(
    audio_path: Path,
    backend: str = "speechbrain",
    hf_token: str | None = None,
    device: str = "auto",
    num_speakers: int | None = None,
) -> list[SpeakerTurn]:
    """Identifica falantes. Backend: 'speechbrain' (CPU, rápido) ou 'pyannote' (GPU)."""
    if backend == "pyannote":
        if not hf_token:
            raise ValueError("--hf-token é obrigatório para o backend pyannote")
        return diarize_pyannote(audio_path, hf_token=hf_token, device=device)

    return diarize_speechbrain(audio_path, num_speakers=num_speakers)


def assign_speakers(
    segments: list[dict],
    turns: list[SpeakerTurn],
) -> list[dict]:
    """Atribui falantes aos segmentos de transcrição por overlap majoritário."""
    for seg in segments:
        best_speaker = None
        best_overlap = 0.0

        for turn in turns:
            overlap_start = max(seg["start"], turn.start)
            overlap_end = min(seg["end"], turn.end)
            overlap = max(0.0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn.speaker

        if best_speaker:
            seg["speaker"] = best_speaker

    return segments
