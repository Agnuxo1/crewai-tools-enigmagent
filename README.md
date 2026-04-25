# crewai-tools-enigmagent

[![CI](https://github.com/Agnuxo1/crewai-tools-enigmagent/actions/workflows/ci.yml/badge.svg)](https://github.com/Agnuxo1/crewai-tools-enigmagent/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/crewai-tools-enigmagent?label=pypi&color=blue)](https://pypi.org/project/crewai-tools-enigmagent/)
[![PyPI downloads](https://img.shields.io/pypi/dm/crewai-tools-enigmagent.svg)](https://pypi.org/project/crewai-tools-enigmagent/)
[![Python](https://img.shields.io/pypi/pyversions/crewai-tools-enigmagent.svg)](https://pypi.org/project/crewai-tools-enigmagent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.40+-orange.svg)](https://github.com/crewAIInc/crewAI)
[![EnigmAgent](https://img.shields.io/badge/EnigmAgent-MCP-purple.svg)](https://github.com/Agnuxo1/EnigmAgent)
[![GitHub stars](https://img.shields.io/github/stars/Agnuxo1/crewai-tools-enigmagent?style=social)](https://github.com/Agnuxo1/crewai-tools-enigmagent)

> **A CrewAI crew of three agents — researcher, writer, GitHub-poster — needs a `GITHUB_TOKEN` to publish the final post to a private repo. CrewAI's recommended pattern is to attach the token to the Agent's LLM config, or pass it through the task description. Both options bake the real token into the prompt context that travels through every model call. If any of those LLM calls is logged, traced, or shipped to a managed provider, the token is now in someone else's database.**

`crewai-tools-enigmagent` is the alternative.

Your crew agent emits `{{GITHUB_TOKEN}}`. The placeholder rides through the LLM context, through the tool input, through every CrewAI trace. Only when the agent calls `EnigmAgentTool` does the placeholder get swapped for the real `ghp_...` value — locally, against an AES-256-GCM encrypted vault, and only if the requesting origin matches the secret's bound domain.

```bash
pip install crewai-tools-enigmagent
```

In another terminal, next to your crew:

```bash
npx enigmagent-mcp --mode rest --port 3737
```

That's the install. The Python package talks to the local EnigmAgent REST server over loopback; secrets stay in the encrypted vault on disk.

> Star [the main project](https://github.com/Agnuxo1/EnigmAgent) if you've ever pasted a token you regretted.

---

## The problem (in CrewAI terms)

When you give a CrewAI agent a credential, you have three options and all three leak:

| Option | What happens |
|---|---|
| Put the token into the Agent's `goal` or task description | It lands in every LLM call the agent makes, in the trace, in the provider's logs |
| Bake the token into a custom tool at construction time | The agent can call the tool with arbitrary inputs and exfiltrate the value indirectly |
| Inject via env var read inside the tool | Works, but you have one long-lived plaintext token sitting in `os.environ` for the whole crew run |

**`crewai-tools-enigmagent` is option D.** Your tasks, your prompts, your traces all carry only `{{PLACEHOLDER}}` strings. The real value is resolved at the boundary, by a process the model cannot see, against a vault on the user's machine.

---

## How it works

```
┌──────────────────┐  emits {{GITHUB_TOKEN}}  ┌─────────────────────┐
│ CrewAI Agent     │ ───────────────────────▶ │  EnigmAgentTool     │
│ (any LLM)        │   + origin parameter     │  ._run(...)         │
└──────────────────┘                          └──────────┬──────────┘
                                                         │ HTTP POST /resolve
                                                         ▼
                                          ┌─────────────────────────┐
                                          │      EnigmAgent         │
                                          │  validates origin,      │
                                          │  decrypts AES-256-GCM   │
                                          │  → ghp_xxx              │
                                          └──────────┬──────────────┘
                                                     │ real value
                                                     ▼
                                          ┌─────────────────────────┐
                                          │  Agent uses value in    │
                                          │  next tool / API call   │
                                          └─────────────────────────┘
```

The model emits a placeholder name + the destination origin. The placeholder lives in the prompt and the trace. `EnigmAgentTool._run()` asks the local EnigmAgent REST server to swap it for the real value — but only if the request's `origin` matches the domain that secret was bound to. Wrong domain → the resolver refuses.

---

## Usage

```python
from crewai import Agent, Crew, Task
from crewai_tools_enigmagent import EnigmAgentTool

enigmagent = EnigmAgentTool()

github_op = Agent(
    role="GitHub Operator",
    goal=(
        "Open a GitHub issue on https://api.github.com using the credentials "
        "stored under the placeholder GITHUB_TOKEN. "
        "Always call the EnigmAgent tool with placeholder='GITHUB_TOKEN' and "
        "origin='https://api.github.com' to retrieve the token; never paste "
        "the raw token into your reasoning."
    ),
    backstory="You operate at the call boundary — secrets stay in the vault.",
    tools=[enigmagent],
)

task = Task(
    description="Open issue 'CI is red' in repo Agnuxo1/example.",
    expected_output="The URL of the created issue.",
    agent=github_op,
)

crew = Crew(agents=[github_op], tasks=[task])
result = crew.kickoff()
```

The agent's reasoning now contains only the placeholder name `GITHUB_TOKEN` and the origin `https://api.github.com`. The plaintext `ghp_...` exists for the duration of the upstream HTTP call and nowhere else.

### Custom client config

```python
from crewai_tools_enigmagent import EnigmAgentClient, EnigmAgentTool

client = EnigmAgentClient(
    base_url="http://127.0.0.1:9999",      # custom port
    timeout=5.0,
    shared_secret="my-loopback-token",      # sent as X-EnigmAgent-Auth header
)

enigmagent = EnigmAgentTool(client=client)
```

To run the EnigmAgent REST server with a shared secret:

```bash
npx enigmagent-mcp --mode rest --port 3737 --auth my-loopback-token
```

---

## The vault

This package is a thin CrewAI wrapper. The real work — Argon2id key derivation, AES-256-GCM encryption, origin binding, audit logging — lives in **[EnigmAgent](https://github.com/Agnuxo1/EnigmAgent)**, the npm package that backs it.

```bash
# Create a vault interactively (one-time)
npx enigmagent-mcp --new-vault ./my.vault.json

# Add a secret bound to a domain
npx enigmagent-mcp --vault ./my.vault.json --add GITHUB_TOKEN ghp_xxx --origin https://api.github.com

# Run as REST server next to your CrewAI app
npx enigmagent-mcp --mode rest --port 3737 --vault ./my.vault.json
```

---

## Security model

- **Loopback only.** The REST server binds to `127.0.0.1`. Only processes on the same machine can reach it.
- **Origin binding.** Every secret is bound to one or more origins (e.g. `https://api.github.com`). Resolving a secret for a different origin is refused.
- **Argon2id + AES-256-GCM.** The vault file is encrypted at rest with a passphrase-derived key.
- **No plaintext in prompts or traces.** The agent's LLM context contains only `{{PLACEHOLDER}}` strings. Resolved values exist only inside the tool's return value, briefly, in the agent's local memory.
- **Optional shared secret.** Pass `--auth` to require an `X-EnigmAgent-Auth` header on every REST call, so unauthorised local processes can't query the vault.

Full threat model: [EnigmAgent THREAT_MODEL.md](https://github.com/Agnuxo1/EnigmAgent/blob/main/docs/THREAT_MODEL.md)

---

## Compatibility

- Python: 3.10, 3.11, 3.12, 3.13
- `crewai >= 0.40`
- `pydantic >= 2`
- Any LLM provider supported by CrewAI (OpenAI, Anthropic, Mistral, Gemini, local via Ollama)

---

## Roadmap

- [ ] `EnigmAgentSubstituteTool` that takes a templated string with multiple `{{PLACEHOLDERS}}` and substitutes them all in one call
- [ ] Optional integration with CrewAI Flows to inject secrets at flow-state boundaries
- [ ] Upstream proposal to `crewai-tools` once this package has real users

PRs welcome.

---

## License

MIT (c) 2026 Francisco Angulo de Lafuente

## Links

- Main project: [github.com/Agnuxo1/EnigmAgent](https://github.com/Agnuxo1/EnigmAgent)
- npm package: [enigmagent-mcp](https://www.npmjs.com/package/enigmagent-mcp)
- LangChain port: [github.com/Agnuxo1/langchain-enigmagent](https://github.com/Agnuxo1/langchain-enigmagent)
- Issues: [github.com/Agnuxo1/crewai-tools-enigmagent/issues](https://github.com/Agnuxo1/crewai-tools-enigmagent/issues)
