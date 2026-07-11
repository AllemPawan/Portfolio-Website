"""
Configuration — everything is env-var driven so you can switch providers
without touching code.

--- LLM (roleplay + judging) ---
LLM_PROVIDER = "anthropic"          -> uses Claude API (pay-per-token, best quality)
LLM_PROVIDER = "openai_compatible"  -> uses any local/OpenAI-compatible server:
                                        Ollama, LM Studio, vLLM, llama.cpp server, etc.

    # Claude API:
    export LLM_PROVIDER="anthropic"
    export ANTHROPIC_API_KEY="sk-ant-..."

    # Fully local via Ollama (free, runs on your machine):
    #   1. install Ollama: https://ollama.com
    #   2. ollama pull llama3.1
    #   3. ollama serve   (usually already running as a service)
    export LLM_PROVIDER="openai_compatible"
    export OPENAI_COMPATIBLE_BASE_URL="http://localhost:11434/v1"
    export OPENAI_COMPATIBLE_MODEL="llama3.1"

--- Speech (all local, no account/API key needed) ---
    pip install faster-whisper transformers torch phonemizer python-Levenshtein \
                sounddevice soundfile numpy
    apt-get install espeak-ng      # required by `phonemizer`
    # Piper TTS: https://github.com/rhasspy/piper -> download a voice .onnx + .json
"""
import os

# --- LLM provider selection ---
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")

OPENAI_COMPATIBLE_BASE_URL = os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:11434/v1")
OPENAI_COMPATIBLE_API_KEY = os.environ.get("OPENAI_COMPATIBLE_API_KEY", "not-needed")
OPENAI_COMPATIBLE_MODEL = os.environ.get("OPENAI_COMPATIBLE_MODEL", "llama3.1")

# --- Local speech tools ---
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")  # tiny/base/small/medium/large-v3
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")  # "cuda" if you have a GPU

PHONEME_MODEL_NAME = os.environ.get("PHONEME_MODEL_NAME", "facebook/wav2vec2-lv-60-espeak-cv-ft")

# Piper voice model (.onnx). Download with:
#   python3 -m piper.download_voices en_US-lessac-medium
# which drops en_US-lessac-medium.onnx (+ .onnx.json) in the current directory.
PIPER_MODEL_PATH = os.environ.get("PIPER_MODEL_PATH", "./en_US-lessac-medium.onnx")

SAMPLE_RATE = 16000
