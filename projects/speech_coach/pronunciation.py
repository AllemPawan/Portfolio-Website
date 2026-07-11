"""
Local, open-source pronunciation scoring — no cloud API.

Approach (a simplified Goodness-of-Pronunciation proxy):
  1. Run a phoneme-recognition wav2vec2 model on the raw audio -> the phonemes
     the speaker actually produced (acoustic, independent of any transcript).
  2. Run the Whisper transcript through `phonemizer` (espeak backend) -> the
     phonemes the speaker was "supposed to" produce, in the same phoneme
     inventory the wav2vec2 model was trained on.
  3. Compare the two phoneme sequences (edit distance) -> an overall accuracy
     score, session-level rather than word-by-word.

HONEST LIMITATION: the "expected" phonemes come from the Whisper transcript, not
a fixed reference script. If Whisper mishears a word *because* it was mispronounced,
the expected phonemes shift to match the error, which softens the signal. This is
the tradeoff for not requiring a scripted-reading mode. If you want stricter,
Azure/scripted-style accuracy, the fix is to have the LLM ask you to read a
specific sentence back, and pass that fixed sentence in as `reference_text`
instead of the Whisper transcript — worth adding if this proxy feels too loose.

Install: pip install transformers torch phonemizer python-Levenshtein
System dep: apt-get install espeak-ng   (phonemizer needs this)
"""
import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from phonemizer import phonemize
import Levenshtein

from config import PHONEME_MODEL_NAME, SAMPLE_RATE

_processor = None
_model = None


def _load():
    global _processor, _model
    if _model is None:
        print(f"Loading phoneme model ({PHONEME_MODEL_NAME})...")
        _processor = Wav2Vec2Processor.from_pretrained(PHONEME_MODEL_NAME)
        _model = Wav2Vec2ForCTC.from_pretrained(PHONEME_MODEL_NAME)
        _model.eval()


def _recognize_phonemes(audio: np.ndarray) -> str:
    _load()
    audio_float = audio.astype(np.float32) / 32768.0
    inputs = _processor(audio_float, sampling_rate=SAMPLE_RATE, return_tensors="pt")
    with torch.no_grad():
        logits = _model(inputs.input_values).logits
    pred_ids = torch.argmax(logits, dim=-1)
    return _processor.batch_decode(pred_ids)[0]


def _expected_phonemes(text: str) -> str:
    # espeak backend produces the same phoneme inventory the wav2vec2 model
    # (facebook/wav2vec2-lv-60-espeak-cv-ft) was trained on.
    return phonemize(text, language="en-us", backend="espeak", strip=True)


def score_pronunciation(audio: np.ndarray, transcript: str) -> dict:
    """
    Returns:
      {
        "phoneme_accuracy": float 0-100,
        "recognized_phonemes": str,
        "expected_phonemes": str,
      }
    """
    if not transcript.strip() or audio.size == 0:
        return {"phoneme_accuracy": 0.0, "recognized_phonemes": "", "expected_phonemes": ""}

    recognized = _recognize_phonemes(audio)
    expected = _expected_phonemes(transcript)

    rec_compact = recognized.replace(" ", "")
    exp_compact = expected.replace(" ", "")

    if not exp_compact:
        return {"phoneme_accuracy": 0.0, "recognized_phonemes": recognized, "expected_phonemes": expected}

    dist = Levenshtein.distance(rec_compact, exp_compact)
    max_len = max(len(rec_compact), len(exp_compact), 1)
    accuracy = max(0.0, (1 - dist / max_len)) * 100

    return {
        "phoneme_accuracy": round(accuracy, 1),
        "recognized_phonemes": recognized,
        "expected_phonemes": expected,
    }


def speech_rate_and_fillers(transcript: str, duration_seconds: float) -> dict:
    """
    Cheap, fully local fluency signals that don't need any model at all —
    just word counting and duration, computed from data we already have.
    """
    fillers = {"um", "uh", "umm", "uhh", "like", "you know", "i mean", "so yeah"}
    words = transcript.lower().split()
    word_count = len(words)
    filler_count = sum(1 for w in words if w.strip(",.?!") in fillers)
    wpm = (word_count / duration_seconds) * 60 if duration_seconds > 0 else 0.0

    return {
        "words_per_minute": round(wpm, 1),
        "filler_word_count": filler_count,
        "word_count": word_count,
    }
