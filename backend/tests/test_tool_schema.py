"""Phase 3.1 — 5.6 invariant 2: the repo under audit is never a model-controlled argument.

`owner` / `repo` used to be tool parameters, so repo content could steer the agent into any
repository the PAT can reach, private ones included. Asserting against the *generated*
schema rather than the source is the point: a re-added parameter, a renamed alias, or an
`InjectedState` annotation that stops being honoured all reopen the hole, and only the
generated payload shows that.
"""

import inspect

from langchain_core.utils.function_calling import convert_to_openai_tool

from agent.subagent_nodes import (
    EVIDENCE_TOOLS,
    get_file_content,
    get_repository_tree,
)
from agent.utils.github_mcp import GitHubMCPManager

REPO_ARGUMENT_NAMES = {"owner", "repo", "repository", "repo_owner", "repo_name", "full_name"}


def schema_properties(tool) -> dict:
    return convert_to_openai_tool(tool)["function"]["parameters"].get("properties", {})


def tool_name(tool) -> str:
    """EVIDENCE_TOOLS mixes StructuredTools with plain functions bind_tools converts."""
    return convert_to_openai_tool(tool)["function"]["name"]


def test_get_file_content_schema_exposes_only_a_path():
    properties = schema_properties(get_file_content)

    assert set(properties) == {"path"}


def test_get_repository_tree_schema_exposes_no_repo_argument():
    properties = schema_properties(get_repository_tree)

    assert set(properties) == {"tree_sha", "recursive", "path_filter"}


def test_no_evidence_tool_can_name_a_repository():
    for tool in EVIDENCE_TOOLS:
        leaked = REPO_ARGUMENT_NAMES & set(schema_properties(tool))
        assert not leaked, f"{tool_name(tool)} exposes {leaked} to the model"


def test_injected_state_is_never_advertised_to_the_model():
    # `state` carries the pinned repo; if it appeared in the schema the model could forge it.
    for tool in EVIDENCE_TOOLS:
        assert "state" not in schema_properties(tool)


def test_the_bound_model_payload_carries_the_same_schemas(monkeypatch):
    """The schema the provider receives is what matters, not the one we can regenerate."""
    captured = {}

    class FakeModel:
        def bind_tools(self, tools):
            captured["tools"] = [convert_to_openai_tool(t) for t in tools]
            return self

    monkeypatch.setattr(
        "agent.subagent_nodes.init_chat_model", lambda **kwargs: FakeModel()
    )
    from agent.subagent_nodes import get_evidence_llm

    get_evidence_llm.cache_clear()
    try:
        get_evidence_llm()
    finally:
        get_evidence_llm.cache_clear()

    for tool_payload in captured["tools"]:
        properties = tool_payload["function"]["parameters"].get("properties", {})
        assert not REPO_ARGUMENT_NAMES & set(properties)


def test_search_codebase_is_not_bound_to_the_evidence_agent():
    # It exists on the manager but takes a raw `repo:owner/name` query string, so binding it
    # would hand the model back the arbitrary-repo access 3.1 removed.
    assert "search_codebase" not in {tool_name(tool) for tool in EVIDENCE_TOOLS}
    assert hasattr(GitHubMCPManager, "search_codebase")


def test_evidence_tool_set_is_exactly_what_the_subagent_expects():
    assert {tool_name(tool) for tool in EVIDENCE_TOOLS} == {
        "get_file_content",
        "get_repository_tree",
        "conclude_evidence",
        "finished_gathering_evidence",
        "think",
    }


def test_the_pinned_repo_comes_from_graph_state_only():
    # Async @tool functions expose the wrapped coroutine, not `.func`.
    source = inspect.getsource(get_file_content.coroutine)
    # The only repo source in the tool body is the state helper.
    assert "_pinned_repo(state)" in source
