"""Framework integrations for averth.

LangChain/LangGraph callback handler and OpenAI SDK client wrapper.
Both are dependency-optional: neither langchain nor openai needs to be
installed to import or unit-test them.
"""

from .langchain import AverthCallbackHandler
from .openai import wrap_openai_client

__all__ = ["AverthCallbackHandler", "wrap_openai_client"]
