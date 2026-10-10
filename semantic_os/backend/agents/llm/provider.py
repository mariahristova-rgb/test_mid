from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# =====================================================
# Chat Message
# =====================================================

@dataclass(slots=True)
class ChatMessage:
    """
    Represents a single chat message.
    """

    role: str

    content: Any

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


# =====================================================
# Generation Request
# =====================================================

@dataclass(slots=True)
class GenerationRequest:
    """
    Generic request sent to an LLM provider.
    """

    messages: list[ChatMessage]

    temperature: float = 0.2

    max_tokens: int = 1024

    top_p: float = 1.0

    stop: list[str] = field(
        default_factory=list
    )

    # Provider-neutral tool schemas (see agents/tools/tool.py's
    # Tool.schema(): {"name", "description", "parameters": {json
    # schema}}), offered to a provider that supports native
    # function/tool calling (see LLMProvider.supports_tools()). A
    # provider without tool support simply ignores this field.
    tools: list[dict[str, Any]] | None = None

    # A supported provider may require a tool call for deterministic
    # integration probes or workflows that cannot continue without one.
    # Normal orchestration leaves this unset and uses the provider default.
    tool_choice: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


# =====================================================
# Generation Response
# =====================================================

@dataclass(slots=True)
class GenerationResponse:
    """
    Generic response returned by an LLM.
    """

    text: str

    model: str

    finish_reason: str = "stop"

    prompt_tokens: int = 0

    completion_tokens: int = 0

    # Native tool/function calls the model asked to make, when the
    # provider and request support it (see GenerationRequest.tools).
    # Each entry is {"id", "name", "input"}. A provider or a
    # tool-less request always leaves this empty, never populated
    # with an invented call.
    tool_calls: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def total_tokens(self) -> int:

        return (

            self.prompt_tokens

            + self.completion_tokens

        )


# =====================================================
# LLM Provider
# =====================================================

class LLMProvider(ABC):
    """
    Base interface for every LLM provider.

    Examples:

        OpenAI

        Azure OpenAI

        Ollama

        Claude

        Gemini

        Local models
    """

    def __init__(

        self,

        model: str,

    ):

        self.model = model

    # -------------------------------------------------

    @property
    def provider_name(self) -> str:

        return self.__class__.__name__

    # -------------------------------------------------

    @abstractmethod
    def generate(

        self,

        request: GenerationRequest,

    ) -> GenerationResponse:
        """
        Generate a completion.
        """
        raise NotImplementedError

    # -------------------------------------------------

    def complete(

        self,

        prompt: str,

        **kwargs,

    ) -> str:
        """
        Convenience wrapper around generate().
        """

        request = GenerationRequest(

            messages=[

                ChatMessage(

                    role="user",

                    content=prompt,

                )

            ],

            **kwargs,

        )

        return self.generate(

            request

        ).text

    # -------------------------------------------------

    def chat(

        self,

        messages: list[ChatMessage],

        **kwargs,

    ) -> GenerationResponse:
        """
        Chat completion.
        """

        request = GenerationRequest(

            messages=messages,

            **kwargs,

        )

        return self.generate(

            request

        )

    # -------------------------------------------------

    def supports_tools(self) -> bool:

        return False

    # -------------------------------------------------

    def supports_streaming(self) -> bool:

        return False

    # -------------------------------------------------

    def supports_embeddings(self) -> bool:

        return False

    # -------------------------------------------------

    def embeddings(

        self,

        texts: list[str],

    ) -> list[list[float]]:
        """
        Optional embedding API.
        """

        raise NotImplementedError(

            f"{self.provider_name} "

            "does not support embeddings."

        )

    # -------------------------------------------------

    def __repr__(self):

        return (

            f"<{self.provider_name}"

            f" model={self.model}>"

        )
