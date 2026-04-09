# Arquitetura

## Visão geral

```
transcrever PATH
    │
    ├── cli.py           → entrada do usuário (Typer)
    ├── pipeline.py      → orquestração
    │   ├── audio.py     → discovery de arquivos + extração ffmpeg
    │   ├── transcriber.py → faster-whisper
    │   ├── diarizer.py  → pyannote.audio (futuro)
    │   └── formatters/  → saída (txt, srt, json)
    └── models.py        → Segment, Transcript (Pydantic)
```

## Fluxo de dados

1. **Discovery** (`audio.py`): recebe um `Path` (arquivo ou diretório), percorre recursivamente e filtra por extensões de áudio/vídeo suportadas.

2. **Extração** (`audio.py`): converte qualquer formato para WAV 16kHz mono via ffmpeg em arquivo temporário.

3. **Transcrição** (`transcriber.py`): usa `faster-whisper` (CTranslate2) para transcrever o WAV. Retorna `Transcript` com lista de `Segment`s.

4. **Formatação** (`formatters/`): converte `Transcript` para o formato de saída (TXT, SRT, JSON).

5. **Saída**: salva o arquivo formatado **na mesma pasta do áudio original**, com a mesma base de nome e extensão do formato.

## Modelos de dados

```python
class Segment(BaseModel):
    start: float        # segundos
    end: float          # segundos
    text: str
    speaker: str | None # None até diarização ser aplicada
    language: str | None

class Transcript(BaseModel):
    source: str                              # caminho do arquivo original
    language: str                            # idioma detectado
    segments: list[Segment]
    metadata: dict[str, str | float | int]   # modelo, device, duração, etc.
```

## Device e compute_type

| Configuração | Device | Compute Type | Quando usar |
|---|---|---|---|
| auto (com GPU) | cuda | float16 | Padrão se GPU CUDA disponível |
| auto (sem GPU) | cpu | int8 | Padrão se só CPU |
| `--device cpu` | cpu | int8 | Forçar CPU |
| `--device cuda` | cuda | float16 | Forçar GPU |

## Dependências opcionais

O projeto usa dependency groups para manter a instalação base leve:

- **Base**: `faster-whisper`, `typer`, `rich`, `pydantic`
- **`[diarize]`**: adiciona `pyannote.audio` + `torch` (~2GB extras)
- **`[dev]`**: `pytest`, `ruff`, `mypy`
