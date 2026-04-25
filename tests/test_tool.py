import pytest
from unittest.mock import patch
from crewai_tools_enigmagent import EnigmAgentClient, EnigmAgentTool, PLACEHOLDER_RE


def test_placeholder_regex():
    assert PLACEHOLDER_RE.findall("Bearer {{TOKEN}} for {{user.id}}") == ["TOKEN", "user.id"]


def test_substitute():
    client = EnigmAgentClient()
    with patch.object(EnigmAgentClient, "resolve", lambda self, p, o: f"<{p}>"):
        out = client.substitute("Authorization: Bearer {{GH_TOKEN}}", origin="https://api.github.com")
    assert out == "Authorization: Bearer <GH_TOKEN>"


def test_list_placeholders():
    client = EnigmAgentClient()
    assert client.list_placeholders("a {{X}} b {{Y}}") == ["X", "Y"]


def test_tool_metadata():
    tool = EnigmAgentTool()
    assert tool.name == "EnigmAgent"
    assert "EnigmAgent" in tool.description
    assert tool.args_schema is not None


def test_tool_run_calls_client_resolve():
    tool = EnigmAgentTool()
    with patch.object(EnigmAgentClient, "resolve", lambda self, p, o: f"resolved::{p}@{o}"):
        out = tool._run(placeholder="GITHUB_TOKEN", origin="https://api.github.com")
    assert out == "resolved::GITHUB_TOKEN@https://api.github.com"


def test_tool_accepts_custom_client():
    custom = EnigmAgentClient(base_url="http://127.0.0.1:9999", shared_secret="abc")
    tool = EnigmAgentTool(client=custom)
    assert tool.client.base_url == "http://127.0.0.1:9999"
    assert tool.client.shared_secret == "abc"
