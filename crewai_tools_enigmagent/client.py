"""HTTP client for the EnigmAgent REST API (localhost:3737 by default)."""
from __future__ import annotations

import re
import httpx
from pydantic import BaseModel, Field

PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z0-9_:\-.@]+)\}\}")


class EnigmAgentClient(BaseModel):
    """Tiny HTTP client around the EnigmAgent REST API.

    Defaults to http://localhost:3737. Run `npx enigmagent-mcp --mode rest --port 3737`
    in a terminal next to your CrewAI application.
    """
    base_url: str = Field(default="http://localhost:3737")
    timeout: float = Field(default=2.0)
    shared_secret: str | None = Field(default=None)

    def _headers(self) -> dict[str, str]:
        return {"X-EnigmAgent-Auth": self.shared_secret} if self.shared_secret else {}

    def status(self) -> dict:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.get(f"{self.base_url}/status", headers=self._headers())
            r.raise_for_status()
            return r.json()

    def list_entries(self) -> list[dict]:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.get(f"{self.base_url}/list", headers=self._headers())
            r.raise_for_status()
            return r.json().get("entries", [])

    def resolve(self, placeholder: str, origin: str) -> str:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(
                f"{self.base_url}/resolve",
                json={"placeholder": placeholder, "origin": origin},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()["value"]

    def substitute(self, text: str, origin: str) -> str:
        """Walk a string and substitute every {{NAME}} occurrence."""
        def repl(m: re.Match[str]) -> str:
            name = m.group(1)
            try:
                return self.resolve(name, origin)
            except httpx.HTTPStatusError as e:
                raise EnigmAgentResolveError(name, e) from e
        return PLACEHOLDER_RE.sub(repl, text)

    def list_placeholders(self, text: str) -> list[str]:
        return [m.group(1) for m in PLACEHOLDER_RE.finditer(text)]


class EnigmAgentResolveError(Exception):
    def __init__(self, placeholder: str, cause: Exception):
        super().__init__(f"Failed to resolve {{{{{placeholder}}}}}: {cause}")
        self.placeholder = placeholder
