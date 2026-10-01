"""Framework integrations for agentpnl.

LangChain/LangGraph callback handler and OpenAI SDK client wrapper.
Both are dependency-optional: neither langchain nor openai needs to be
installed to import or unit-test them.
"""

from .langchain import AgentPNLCallbackHandler
from .openai import wrap_openai_client

__all__ = ["AgentPNLCallbackHandler", "wrap_openai_client"]
