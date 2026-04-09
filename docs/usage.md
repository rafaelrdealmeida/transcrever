# Uso

## Comandos

### Transcrever arquivo único

```bash
uv run transcrever ./entrevista.m4a
```

Gera `entrevista.txt` na mesma pasta.

### Transcrever pasta inteira

```bash
uv run transcrever ./arquivos/
```

Descobre todos os arquivos de áudio/vídeo recursivamente nas subpastas e gera um `.txt` ao lado de cada um.

**Exemplo:**
```
arquivos/
├── Entrevista 1/
│   ├── parte1.m4a
│   ├── parte1.txt  ← gerado
│   ├── parte2.m4a
│   └── parte2.txt  ← gerado
└── Entrevista 2/
    ├── audio.m4a
    └── audio.txt    ← gerado
```

## Opções

### `--model, -m`

Modelo Whisper a usar. Default: `medium`.

```bash
# Rápido mas menos preciso
uv run transcrever ./audio.m4a -m tiny

# Mais preciso mas mais lento
uv run transcrever ./audio.m4a -m large-v3
```

### `--language, -l`

Força um idioma específico (útil quando a detecção automática erra).

```bash
uv run transcrever ./audio.m4a -l pt   # Português
uv run transcrever ./audio.m4a -l es   # Espanhol
uv run transcrever ./audio.m4a -l en   # Inglês
```

### `--device, -d`

Controla o dispositivo de computação. Default: `auto` (GPU se disponível, senão CPU).

```bash
uv run transcrever ./audio.m4a -d cpu    # Forçar CPU
uv run transcrever ./audio.m4a -d cuda   # Forçar GPU
```

### `--format, -f`

Formato de saída. Default: `txt`.

```bash
uv run transcrever ./audio.m4a -f txt
```

Formatos futuros: `srt`, `json`.

## Formatos suportados

### Áudio
`.m4a`, `.mp3`, `.wav`, `.ogg`, `.flac`, `.wma`, `.aac`

### Vídeo
`.mp4`, `.mkv`, `.webm`, `.avi`, `.mov`

## Formato de saída TXT

```
[00:00:00 - 00:00:05] Olá, muito obrigado por me receber.
[00:00:06 - 00:00:12] De nada, é um prazer participar desta entrevista.
```

Com diarização (futuro):
```
[00:00:00 - 00:00:05] [Falante 1] Olá, muito obrigado por me receber.
[00:00:06 - 00:00:12] [Falante 2] De nada, é um prazer participar desta entrevista.
```
