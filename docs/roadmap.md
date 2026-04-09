# Roadmap — Transcrever

Ferramenta CLI para transcrição automatizada de áudio/vídeo com identificação de falantes e suporte multilíngue.

## Stack tecnológica

| Componente | Biblioteca | Por quê |
|---|---|---|
| Transcrição | **faster-whisper** | 4x mais rápido que Whisper, 99+ idiomas, MIT |
| Diarização | **pyannote.audio 3.1+** | Melhor diarização open-source (~11% DER), MIT |
| CLI | **typer + rich** | CLI moderna com progress bars |
| Modelos de dados | **pydantic** | Validação e serialização tipada |
| Áudio | **ffmpeg** | Extração/conversão de qualquer formato |
| Pacotes | **uv** | Gerenciamento rápido de dependências Python |

---

## Fase 1 — Transcrição básica (MVP)

**Objetivo:** `transcrever ./pasta/` transcreve todos os áudios e salva `.txt` ao lado de cada arquivo.

### Funcionalidades
- Apontar para uma pasta → descobre subpastas e arquivos de áudio recursivamente
- Apontar para um arquivo único → transcreve direto
- Extensões suportadas: `.m4a`, `.mp3`, `.wav`, `.ogg`, `.flac`, `.mp4`, `.mkv`, `.webm`
- Extração de áudio via ffmpeg (→ WAV 16kHz mono temporário)
- Transcrição com faster-whisper (detecção automática de idioma)
- Saída em `.txt` salva na mesma pasta do áudio original
- Progress bar com rich durante o processamento
- Seleção de modelo: `--model tiny|base|small|medium|large-v3`
- Detecção automática de GPU/CPU com fallback

### Arquivos
- `src/transcrever/models.py` — Segment, Transcript (Pydantic)
- `src/transcrever/config.py` — detect_device(), extensões, defaults
- `src/transcrever/audio.py` — discover_audio_files(), extract_audio()
- `src/transcrever/transcriber.py` — transcribe() com faster-whisper
- `src/transcrever/formatters/txt.py` — formata Transcript como texto
- `src/transcrever/pipeline.py` — orquestração completa
- `src/transcrever/cli.py` — entrada Typer

### Verificação
```bash
uv run transcrever ./arquivos/
# Cada .m4a ganha um .txt ao lado com a transcrição
```

---

## Fase 2 — Diarização (identificação de falantes)

**Objetivo:** `transcrever ./pasta/ --diarize` identifica quem falou cada trecho.

### Funcionalidades
- Integração com pyannote.audio 3.1+ para speaker diarization
- Merge de transcrição + diarização por overlap majoritário
- Labels `[Falante 1]`, `[Falante 2]` na saída
- Flag `--diarize` (desativado por padrão, requer `transcrever[diarize]`)
- Token HuggingFace via `--hf-token` ou variável `HF_TOKEN`
- `--max-speakers N` para limitar número de falantes

### Arquivos
- `src/transcrever/diarizer.py` — diarize() com pyannote
- Atualização de `pipeline.py` e `formatters/txt.py`

### Verificação
```bash
uv pip install transcrever[diarize]
uv run transcrever ./arquivos/ --diarize --hf-token $HF_TOKEN
# Saída com identificação de falantes
```

---

## Fase 3 — Formatos de saída

**Objetivo:** Suporte a múltiplos formatos de saída além de TXT.

### Funcionalidades
- **SRT** — legendas com timestamps (`HH:MM:SS,mmm`), speaker labels opcionais
- **JSON** — estruturado com todos os metadados (modelo, idioma, duração, segmentos)
- Flag `--format txt|srt|json` (default: txt)

### Arquivos
- `src/transcrever/formatters/srt.py`
- `src/transcrever/formatters/json_fmt.py`

### Verificação
```bash
uv run transcrever ./arquivos/ --format srt
uv run transcrever ./arquivos/ --format json --diarize
```

---

## Fase 4 — Polish e otimização

**Objetivo:** Melhorias de performance e usabilidade.

### Funcionalidades
- Cache do modelo Whisper no batch (carregar 1x, transcrever N arquivos)
- `--word-timestamps` para timestamps por palavra
- Comando `transcrever info` — mostra device, modelos disponíveis, versão ffmpeg
- Arquivo de config `transcrever.toml` para defaults persistentes
- Flag `--skip-existing` para pular arquivos já transcritos
- Resumo final detalhado (arquivos processados, tempo total, idiomas detectados)
