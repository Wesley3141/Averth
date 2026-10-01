"""Deterministic local stub chat model for the validation agent.

NO model API is available in this environment (no langchain openai/anthropic
provider packages, no API keys). This stub replaces the LLM ONLY for
orchestration decisions (plan formatting, report summarization). Token
counts are REAL measurements: tiktoken (cl100k_base) over the actual prompt
text sent and the actual completion text produced. Cost is priced through
averth's documented estimate fallback and flagged in unpriced_models.

Everything else is real: real LangGraph dispatch, real callback events,
real HTTP tool calls, real latency, real failures, real retries.
"""
import tiktoken
from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk

ENC = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(ENC.encode(text))


def messages_text(messages: List[BaseMessage]) -> str:
    return "\n".join(f"{m.type}: {m.content}" for m in messages)


class StubChatModel(BaseChatModel):
    """Deterministic rule-based stand-in for an LLM.

    _respond() is a pure function of the input messages: the "plan" prompt
    yields a tool plan, anything else yields a summary of the supplied
    context. Both branches are fully deterministic (no randomness).
    """

    model_name: str = "averth-stub-1"

    @property
    def _llm_type(self) -> str:
        return "averth-stub"

    def _respond(self, messages: List[BaseMessage]) -> str:
        full = messages_text(messages)
        if "PLAN_REQUEST" in full:
            query = ""
            for m in messages:
                if m.type == "human":
                    query = str(m.content)
            query = query.replace("PLAN_REQUEST", "").strip()
            words = query.split()
            topic = " ".join(words[:6])
            return (
                '{"tools": ["web_search", "github_api"], '
                f'"topic": "{topic}", "strategy": "fan-out parallel lookup"}}'
            )
        # report branch: summarize provided context deterministically
        ctx = full[-1200:]
        return (
            "Summary of gathered evidence: " + ctx[:400].replace("\n", " ")
            + " ... Key finding: sources agree the topic is actively discussed. "
            "Confidence: medium. No further tool calls needed."
        )

    def _usage(self, messages: List[BaseMessage], text: str):
        return {
            "prompt_tokens": count_tokens(messages_text(messages)),
            "completion_tokens": count_tokens(text),
        }

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs,
    ) -> ChatResult:
        text = self._respond(messages)
        usage = self._usage(messages, text)
        if run_manager:
            for chunk_text in _chunks(text):
                run_manager.on_llm_new_token(chunk_text)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))],
            llm_output={"token_usage": usage},
        )

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs,
    ):
        text = self._respond(messages)
        for chunk_text in _chunks(text):
            yield ChatGenerationChunk(message=AIMessageChunk(content=chunk_text))


def _chunks(text: str, size: int = 24):
    for i in range(0, len(text), size):
        yield text[i : i + size]
