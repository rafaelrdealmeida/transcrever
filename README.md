# transcrever

CLI para transcrição automatizada de áudio/vídeo com identificação de falantes e suporte multilíngue.

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
```

A transcrição é salva como `.txt` na mesma pasta do áudio original.

## Opções

| Opção | Descrição | Default |
|---|---|---|
| `--model, -m` | Modelo Whisper (tiny, base, small, medium, large-v3) | medium |
| `--language, -l` | Código do idioma (pt, es, en...) | auto |
| `--device, -d` | Device (auto, cpu, cuda) | auto |
| `--format, -f` | Formato de saída (txt) | txt |

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
│   ├── pipeline.py                 # Orquestração com progress bar
│   └── formatters/
│       └── txt.py                  # Saída em texto com timestamps
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
