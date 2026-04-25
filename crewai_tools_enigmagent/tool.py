"""EnigmAgentTool — a CrewAI BaseTool that resolves {{PLACEHOLDER}} secrets
from the local EnigmAgent vault, scoped to a requesting origin.
"""
from __future__ import annotations

from typing import Type, Optional
from pydantic import BaseModel, Field, PrivateAttr

from crewai.tools import BaseTool

from .client import EnigmAgentClient


class EnigmAgentInput(BaseModel):
    """Input schema for EnigmAgentTool."""
    placeholder: str = Field(
        ...,
        description="The placeholder name (without surrounding braces) to resolve, "
                    "e.g. 'GITHUB_TOKEN' for the placeholder {{GITHUB_TOKEN}}.",
    )
    origin: str = Field(
        ...,
        description="The requesting origin URL (e.g. 'https://api.github.com'). "
                    "Must match the secret's bound domain or resolution is refused.",
    )


class EnigmAgentTool(BaseTool):
    """CrewAI tool that resolves a single secret from the EnigmAgent vault.

    Give this tool to any CrewAI agent that needs to call an authenticated API.
    The agent emits the placeholder name and the destination origin; the tool
    asks the local EnigmAgent REST server (loopback, encrypted vault) to swap
    it for the real value. The plaintext exists only inside the agent's tool
    output for the duration of the upstream call. The LLM never sees the secret
    in its prompt — it only ever emits the placeholder.

    Example:
        from crewai import Agent, Crew, Task
        from crewai_tools_enigmagent import EnigmAgentTool

        github_agent = Agent(
            role="GitHub Operator",
            goal="Open issues using {{GITHUB_TOKEN}} on api.github.com",
            tools=[EnigmAgentTool()],
        )
    """

    name: str = "EnigmAgent"
    description: str = (
        "Resolve a {{PLACEHOLDER}} secret from the EnigmAgent local vault. "
        "Inputs: `placeholder` (e.g. 'GITHUB_TOKEN'), `origin` (e.g. "
        "'https://api.github.com'). Returns the decrypted value only when the "
        "requesting origin matches the secret's bound domain; otherwise the "
        "vault refuses and the tool errors. Use this whenever you need an API "
        "key, token, or password — never put real secrets in a prompt."
    )
    args_schema: Type[BaseModel] = EnigmAgentInput

    _client: EnigmAgentClient = PrivateAttr()

    def __init__(self, client: Optional[EnigmAgentClient] = None, **data):
        super().__init__(**data)
        self._client = client or EnigmAgentClient()

    @property
    def client(self) -> EnigmAgentClient:
        return self._client

    def _run(self, placeholder: str, origin: str) -> str:
        return self._client.resolve(placeholder, origin)
