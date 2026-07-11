# Speech Coach — Live Roleplay Practice with AI

Practice spoken English through live roleplay conversations and get structured coaching feedback — grammar corrections, fluency analysis, pronunciation trends, and prioritized improvement areas. Entire pipeline runs locally with open-source models; the LLM for roleplay and judging is switchable between Claude API and any OpenAI-compatible local server.

## How It Works

```
You speak → STT (faster-whisper) → LLM roleplay partner → TTS (Piper) → repeat
                                                                              ↓
                                  End of session → Coaching report (grammar, fluency, pronunciation)
```

You pick a scenario (Job Interview, Small Talk, Friendly Debate), the AI partner starts the conversation, and you respond out loud. The partner hears you, replies audibly, and keeps the conversation going until you say "stop the session." At the end, you get a structured coaching report saved to JSON for progress tracking.

## Stack

| Component | Tool | Runs |
|---|---|---|
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local (CPU/GPU) |
| Pronunciation Scoring | wav2vec2 phoneme model + [phonemizer](https://github.com/bootphon/phonemizer) | Local |
| Text-to-Speech | [Piper](https://github.com/rhasspy/piper) | Local |
| LLM (Roleplay + Judging) | Claude API or OpenAI-compatible (Ollama, LM Studio, vLLM) | Configurable |

## Project Structure

```
speech_coach/
├── main.py             # Entry point — run a live session
├── conversation.py     # Roleplay conversation manager (LLM calls)
├── scenarios.py        # Scenario definitions (interview, small talk, debate)
├── feedback.py         # End-of-session coaching report generation
├── speech_io.py        # Audio I/O — record, transcribe, speak
├── pronunciation.py    # Local pronunciation scoring + fluency metrics
├── llm_client.py       # LLM abstraction (Anthropic / OpenAI-compatible)
├── config.py           # Environment-variable-driven configuration
├── requirements.txt    # Python dependencies
└── speech_coach_colab.ipynb  # Jupyter notebook version for Colab
```

## Quick Start

### 1. Install dependencies

```bash
pip install faster-whisper transformers torch phonemizer python-Levenshtein \
            sounddevice soundfile numpy anthropic openai piper-tts
```

System dependency for phoneme analysis:

```bash
# Linux
sudo apt-get install espeak-ng
# macOS
brew install espeak
```

### 2. Download a Piper voice

```bash
python3 -m piper.download_voices en_US-lessac-medium
```

### 3. Configure LLM provider

**Claude API** (best quality):

```bash
export LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Fully local** via Ollama (free):

```bash
ollama pull llama3.1
export LLM_PROVIDER="openai_compatible"
export OPENAI_COMPATIBLE_BASE_URL="http://localhost:11434/v1"
export OPENAI_COMPATIBLE_MODEL="llama3.1"
```

### 4. Run

```bash
python main.py
```

Pick a scenario, then just talk. Say "stop the session" when done.

## Features

- **Live spoken conversation** — the AI partner speaks back via neural TTS, not text
- **3 scenarios** — Job Interview, Small Talk, Friendly Debate
- **Local pronunciation scoring** — phoneme-level comparison using wav2vec2 (no cloud API)
- **Fluency signals** — words-per-minute and filler word counts per turn
- **Coaching report** — structured feedback with strengths, grammar corrections, fluency notes, top 3 priorities, and specific learning resources
- **Session logging** — every session saved to `session_logs/*.json` for progress tracking
- **LLM-agnostic** — switch between Claude and local models via a single env var

## Pronunciation Scoring Caveat

Without a fixed reference script, "expected" phonemes come from the Whisper transcript. If Whisper mishears a word that was mispronounced, the expected phonemes shift to match the error. Treat the score as a rough session-level trend signal, not a precise per-word grade.

## Configuration

All settings via environment variables — see `config.py` for the full list:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai_compatible` |
| `WHISPER_MODEL_SIZE` | `small` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `PIPER_MODEL_PATH` | `./en_US-lessac-medium.onnx` | Path to Piper voice model |

## License

MIT
