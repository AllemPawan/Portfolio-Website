"""
All audio in/out, fully local:
  - record_until_silence(): captures mic audio until you pause
  - transcribe(): STT via faster-whisper (runs locally, no API)
  - speak(): TTS via Piper (runs locally, no API)

Install: pip install faster-whisper sounddevice soundfile numpy piper-tts
Then download a voice once: python3 -m piper.download_voices en_US-lessac-medium
"""
import os
import queue
import tempfile
import time
import wave

import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
from piper import PiperVoice

from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, SAMPLE_RATE, PIPER_MODEL_PATH

_whisper_model = None
_piper_voice = None


def _get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        print(f"Loading Whisper model ({WHISPER_MODEL_SIZE})...")
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type="int8")
    return _whisper_model


def record_until_silence(
    max_duration: float = 30.0,
    silence_threshold: int = 400,
    silence_duration: float = 1.2,
) -> np.ndarray:
    """
    Records from the default mic until the user pauses (energy-based, no extra
    VAD dependency needed). Returns int16 mono samples at SAMPLE_RATE.

    Tune silence_threshold if it's cutting you off too early (raise it in a
    noisy room) or waiting too long (lower it in a quiet room).
    """
    q: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata.copy())

    print("🎤 Listening... (speak now, pause when done)")
    frames = []
    silence_start = None
    speech_started = False
    start_time = time.time()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback):
        while True:
            if time.time() - start_time > max_duration:
                break
            try:
                chunk = q.get(timeout=0.5)
            except queue.Empty:
                continue
            frames.append(chunk)
            volume = np.abs(chunk).mean()

            if volume > silence_threshold:
                speech_started = True
                silence_start = None
            elif speech_started:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > silence_duration:
                    break

    if not frames:
        return np.array([], dtype=np.int16)
    return np.concatenate(frames, axis=0).flatten()


def transcribe(audio: np.ndarray) -> str:
    if audio.size == 0:
        return ""
    model = _get_whisper_model()
    audio_float = audio.astype(np.float32) / 32768.0
    segments, _ = model.transcribe(audio_float, language="en", beam_size=5)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _get_piper_voice() -> PiperVoice:
    global _piper_voice
    if _piper_voice is None:
        if not os.path.exists(PIPER_MODEL_PATH):
            raise FileNotFoundError(
                f"Piper voice not found at {PIPER_MODEL_PATH}. Download one with:\n"
                f"  python3 -m piper.download_voices en_US-lessac-medium"
            )
        _piper_voice = PiperVoice.load(PIPER_MODEL_PATH)
    return _piper_voice


def speak(text: str):
    """Speaks text aloud via Piper (local, offline neural TTS)."""
    voice = _get_piper_voice()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name

    try:
        with wave.open(out_path, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        data, sr = sf.read(out_path, dtype="int16")
        sd.play(data, sr)
        sd.wait()
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
