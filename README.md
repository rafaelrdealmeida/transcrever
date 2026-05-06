# transcrever

CLI para transcrição automatizada de áudio/vídeo com identificação de falantes e suporte multilíngue.

## Formatos suportados

| Tipo | Extensões |
|---|---|
| Áudio | `.m4a` `.mp3` `.wav` `.ogg` `.flac` `.wma` `.aac` |
| Vídeo | `.mp4` `.mkv` `.webm` `.avi` `.mov` |

O áudio é extraído automaticamente de arquivos de vídeo via ffmpeg.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- ffmpeg (`sudo apt install ffmpeg`)

## Instalação

```bash
uv sync
```

Para suporte a diarização (identificação de falantes):

```bash
uv sync --extra diarize
```

## Uso

```bash
# Transcrever um arquivo
uv run transcrever ./audio.m4a

# Transcrever todos os áudios de uma pasta (recursivo)
uv run transcrever ./arquivos/

# Especificar modelo e idioma
uv run transcrever ./arquivos/ --model large-v3 --language pt

# Com diarização (identificação de falantes)
uv run transcrever ./arquivos/ --diarize --diarize-backend pyannote --num-speakers 2
```

Para cada arquivo, são gerados 3 arquivos na mesma pasta:

| Arquivo | Conteúdo |
|---|---|
| `<nome>_01_bruto.txt` | Texto puro, sem falantes nem timestamps |
| `<nome>_02_pessoas.txt` | Texto corrido agrupado por falante |
| `<nome>_03_tempo_pessoas.txt` | Transcrição com diarização e marcação temporal |

## Opções

| Opção | Descrição | Default |
|---|---|---|
| `--model, -m` | Modelo Whisper (tiny, base, small, medium, large-v3) | medium |
| `--language, -l` | Código do idioma (pt, es, en...) | auto |
| `--device, -d` | Device (auto, cpu, cuda) | auto |
| `--format, -f` | Formato de saída (txt) | txt |
| `--diarize` | Ativar identificação de falantes | off |
| `--diarize-backend` | Backend: speechbrain (CPU) ou pyannote (GPU) | speechbrain |
| `--hf-token` | Token HuggingFace para pyannote (ou use HF_TOKEN no .env) | — |
| `--num-speakers, -n` | Número de falantes | — |

## Transcrição via GPU remota (Vast.ai)

Para transcrever todos os áudios usando uma GPU alugada na Vast.ai:

1. Configure o `.env` (veja `.env.example`)
2. Instale o CLI: `uv sync --extra vastai`
3. Registre sua chave SSH em https://cloud.vast.ai/account/
4. Execute:

```bash
uv run python scripts/vastai_transcribe.py
```

O script provisiona uma GPU, transcreve tudo com `large-v3` + pyannote, baixa os resultados e destrói a instância automaticamente.

## Estrutura do projeto

```
transcrever/
├── pyproject.toml                  # Configuração do projeto (uv + hatchling)
├── .python-version                 # Python 3.11
├── src/transcrever/
│   ├── cli.py                      # CLI (Typer)
│   ├── config.py                   # Detecção de device, extensões suportadas
│   ├── models.py                   # Segment, Transcript (Pydantic)
│   ├── audio.py                    # Discovery de arquivos + extração ffmpeg
│   ├── transcriber.py              # Transcrição com faster-whisper
│   ├── diarizer.py                 # Identificação de falantes (speechbrain/pyannote)
│   ├── pipeline.py                 # Orquestração com progress bar
│   └── formatters/
│       └── txt.py                  # Saída em texto com timestamps
├── scripts/
│   └── vastai_transcribe.py        # Pipeline autônomo via Vast.ai GPU
├── docs/
│   ├── roadmap.md                  # Roadmap de desenvolvimento
│   ├── installation.md             # Guia de instalação
│   ├── usage.md                    # Referência da CLI
│   └── architecture.md             # Decisões técnicas
└── tests/
```

## Documentação

Veja a pasta [docs/](docs/) para documentação detalhada:

- [Roadmap](docs/roadmap.md) — fases de desenvolvimento
- [Instalação](docs/installation.md) — guia completo de setup
- [Uso](docs/usage.md) — referência da CLI
- [Arquitetura](docs/architecture.md) — decisões técnicas
