"""
Manages the back-and-forth with the LLM playing the roleplay character.
Works identically regardless of which provider is configured (see llm_client.py).
"""
from llm_client import LLMClient


class RoleplayConversation:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.messages = []  # [{"role": "user"/"assistant", "content": str}, ...]
        self.llm = LLMClient()

    def add_user_turn(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def get_reply(self) -> str:
        reply = self.llm.chat(self.system_prompt, self.messages, max_tokens=300)
        self.messages.append({"role": "assistant", "content": reply})
        return reply
