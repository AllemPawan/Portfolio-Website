"""
End-of-session feedback: combines the full transcript with locally-computed
pronunciation/fluency signals, and asks the LLM to synthesize concrete,
prioritized coaching feedback.
"""
from statistics import mean
from llm_client import LLMClient

FEEDBACK_SYSTEM_PROMPT = """You are an expert spoken-English coach reviewing a practice
session transcript. You're given:
  1. The full conversation transcript (user's spoken turns + partner's replies)
  2. Aggregated local pronunciation/fluency signals per turn:
     - phoneme_accuracy: an approximate 0-100 score from comparing recognized vs.
       expected phonemes (this is a local, open-source approximation, not a
       clinical-grade pronunciation assessment — treat it as a rough signal, and
       say so if the number seems inconsistent with the transcript quality)
     - words_per_minute and filler_word_count per turn

Give feedback that is specific and actionable, not generic encouragement. Structure your
response as:

**Strengths** (2-3 concrete things, quoting or referencing specific moments from the transcript)

**Grammar & Phrasing Issues** (specific sentences that had errors, with the corrected version)

**Fluency Notes** (filler words, pace, hesitation patterns — based on the transcript and the
words_per_minute/filler_word_count signals)

**Pronunciation** (based on the phoneme_accuracy signal — note this is an approximate local
score, not word-level detail, so keep this section general: overall trend across the
session, not claims about specific sounds)

**Top 3 Priorities** (the 3 things that would most improve their spoken English if fixed first,
ranked by impact)

**Resources** (2-4 specific, real resources — e.g. named YouTube channels, apps, specific
exercises like shadowing or minimal pairs drills — matched to the priorities above, not generic
"practice more" advice)

Be direct and honest. Do not pad with excessive praise. This is a coaching report, not a
pep talk."""


def generate_report(turns: list[dict]) -> str:
    """
    turns: list of dicts, one per user turn:
        {
          "transcript": str,
          "assistant_reply": str,
          "phoneme_accuracy": float,
          "words_per_minute": float,
          "filler_word_count": int,
        }
    """
    valid_turns = [t for t in turns if t["transcript"]]
    if not valid_turns:
        return "No speech was captured this session — nothing to give feedback on."

    transcript_lines = []
    for i, t in enumerate(valid_turns, 1):
        transcript_lines.append(f"[Turn {i}] You: {t['transcript']}")
        transcript_lines.append(f"[Turn {i}] Partner: {t['assistant_reply']}")
    transcript_text = "\n".join(transcript_lines)

    avg_phoneme = mean(t["phoneme_accuracy"] for t in valid_turns)
    avg_wpm = mean(t["words_per_minute"] for t in valid_turns)
    total_fillers = sum(t["filler_word_count"] for t in valid_turns)

    user_content = f"""SESSION TRANSCRIPT:
{transcript_text}

AGGREGATE LOCAL SIGNALS:
- Average phoneme accuracy (approximate, 0-100): {avg_phoneme:.1f}
- Average speaking pace: {avg_wpm:.1f} words/minute
- Total filler words used across session: {total_fillers}

Please generate the coaching report."""

    llm = LLMClient()
    return llm.chat(FEEDBACK_SYSTEM_PROMPT, [{"role": "user", "content": user_content}], max_tokens=1500)
