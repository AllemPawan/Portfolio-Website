"""
LLM abstraction — lets conversation.py and feedback.py call a single .chat()
method regardless of whether the backend is Claude's API or a local/OpenAI-
compatible server (Ollama, LM Studio, vLLM, llama.cpp server, etc).

Switch providers purely via config.py / environment variables — no code changes.
"""
from config import LLM_PROVIDER


class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER

        if self.provider == "anthropic":
            from anthropic import Anthropic
            from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
            if not ANTHROPIC_API_KEY:
                raise EnvironmentError(
                    "LLM_PROVIDER is 'anthropic' but ANTHROPIC_API_KEY is not set. "
                    "Either set the key, or set LLM_PROVIDER=openai_compatible to run "
                    "fully locally instead."
                )
            self._client = Anthropic(api_key=ANTHROPIC_API_KEY)
            self._model = CLAUDE_MODEL

        elif self.provider == "openai_compatible":
            from openai import OpenAI
            from config import (
                OPENAI_COMPATIBLE_BASE_URL,
                OPENAI_COMPATIBLE_API_KEY,
                OPENAI_COMPATIBLE_MODEL,
            )
            self._client = OpenAI(
                base_url=OPENAI_COMPATIBLE_BASE_URL,
                api_key=OPENAI_COMPATIBLE_API_KEY,
            )
            self._model = OPENAI_COMPATIBLE_MODEL

        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.provider}'. Use 'anthropic' or 'openai_compatible'."
            )

    def chat(self, system_prompt: str, messages: list[dict], max_tokens: int = 500) -> str:
        """
        messages: [{"role": "user"/"assistant", "content": str}, ...]
        (no system message in this list — passed separately, matching Claude's API shape;
        translated automatically for OpenAI-compatible servers)
        """
        if self.provider == "anthropic":
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text

        else:  # openai_compatible
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=full_messages,
            )
            return response.choices[0].message.content
