"""A stand-in for the OpenAI SDK client, so the live-API code path is tested without credits."""
from types import SimpleNamespace


class FakeOpenAI:
    """`replies` is a list of strings (model text) or Exceptions, returned in order."""

    def __init__(self, replies, prompt_tokens=100, completion_tokens=50):
        self.replies = list(replies)
        self.requests = []
        self.prompt_tokens, self.completion_tokens = prompt_tokens, completion_tokens
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(prompt_tokens=self.prompt_tokens, completion_tokens=self.completion_tokens),
        )
