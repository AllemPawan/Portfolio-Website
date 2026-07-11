"""
Entry point: run a live roleplay speech-practice session, fully local except
for whichever LLM_PROVIDER you configure (see config.py).

Usage:
    python main.py

Flow:
  1. Pick a scenario (interview / small talk / debate)
  2. The partner opens the conversation (spoken aloud via Piper)
  3. Loop: you speak -> transcribed (faster-whisper) + pronunciation-scored
     (local wav2vec2) -> partner replies (spoken aloud)
     Say "stop the session" (or similar) at any point to end.
  4. Get a written coaching report at the end.
"""
from datetime import datetime
import json
import os
import time

from scenarios import SCENARIOS, choose_scenario
from conversation import RoleplayConversation
from speech_io import record_until_silence, transcribe, speak
from pronunciation import score_pronunciation, speech_rate_and_fillers
from feedback import generate_report
from config import SAMPLE_RATE

STOP_PHRASES = {"stop the session", "end session", "stop session", "that's all", "let's stop"}


def run_session():
    scenario_key = choose_scenario()
    scenario = SCENARIOS[scenario_key]

    convo = RoleplayConversation(system_prompt=scenario["system_prompt"])
    turns = []

    opening = scenario["opening"]
    print(f"\nPartner: {opening}\n")
    speak(opening)
    convo.messages.append({"role": "assistant", "content": opening})

    print("(Say a stop phrase like 'stop the session' when you want to end.)\n")

    while True:
        audio = record_until_silence()
        duration_seconds = audio.size / SAMPLE_RATE if audio.size else 0.0

        transcript = transcribe(audio).strip()
        if not transcript:
            print("(Didn't catch that — try again.)")
            continue

        print(f"You: {transcript}")

        if transcript.lower().strip(".!?") in STOP_PHRASES:
            print("\nEnding session...\n")
            break

        pron = score_pronunciation(audio, transcript)
        fluency = speech_rate_and_fillers(transcript, duration_seconds)

        convo.add_user_turn(transcript)
        reply = convo.get_reply()
        print(f"Partner: {reply}\n")
        speak(reply)

        turns.append({
            "transcript": transcript,
            "assistant_reply": reply,
            "phoneme_accuracy": pron["phoneme_accuracy"],
            "words_per_minute": fluency["words_per_minute"],
            "filler_word_count": fluency["filler_word_count"],
        })

    if not turns:
        print("No turns recorded — ending without a report.")
        return

    print("Generating your coaching report...\n")
    report = generate_report(turns)
    print("=" * 60)
    print(report)
    print("=" * 60)

    os.makedirs("session_logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"session_logs/session_{scenario_key}_{timestamp}.json"
    with open(log_path, "w") as f:
        json.dump({"scenario": scenario_key, "turns": turns, "report": report}, f, indent=2)
    print(f"\nSession saved to {log_path}")


if __name__ == "__main__":
    run_session()
