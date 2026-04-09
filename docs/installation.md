# Instalação

## Pré-requisitos

### Python 3.11+

```bash
python3 --version
```

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### ffmpeg

O ffmpeg é necessário para extrair e converter áudio de qualquer formato.

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Verificar instalação
ffmpeg -version
```

## Instalação do projeto

```bash
# Clonar o repositório
git clone <repo-url>
cd transcrever

# Instalar dependências
uv sync
```

## GPU (opcional)

O `faster-whisper` usa CTranslate2 e detecta automaticamente se há GPU CUDA disponível.

- **Com GPU**: usa `float16` (mais rápido)
- **Sem GPU**: usa `int8` no CPU (funciona bem, só mais lento)

Para forçar CPU:

```bash
uv run transcrever ./audio.m4a --device cpu
```

## Modelos Whisper

| Modelo | Tamanho | VRAM | Velocidade | Qualidade |
|---|---|---|---|---|
| tiny | ~75 MB | ~1 GB | Muito rápido | Baixa |
| base | ~150 MB | ~1 GB | Rápido | Razoável |
| small | ~500 MB | ~2 GB | Médio | Boa |
| **medium** | ~1.5 GB | ~5 GB | Médio-lento | **Muito boa** |
| large-v3 | ~3 GB | ~10 GB | Lento | Excelente |

O modelo padrão é `medium` — bom equilíbrio entre qualidade e velocidade para português/espanhol.

## Diarização (identificação de falantes)

A diarização usa o `pyannote.audio` e requer um token do HuggingFace:

1. Crie uma conta em [huggingface.co](https://huggingface.co)
2. Aceite os termos do modelo [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. Gere um token em [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

```bash
# Instalar dependências de diarização
uv sync --extra diarize

# Usar
uv run transcrever ./audio.m4a --diarize --hf-token SEU_TOKEN

# Ou via variável de ambiente
export HF_TOKEN=SEU_TOKEN
uv run transcrever ./audio.m4a --diarize
```
