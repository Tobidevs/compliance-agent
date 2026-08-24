import asyncio
import json
import os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from functools import cache
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import tool
from dotenv import load_dotenv
from pydantic import BaseModel

from ..untrusted import DIRECTORY_TAG, FILE_TAG, TREE_TAG, wrap_untrusted

load_dotenv()

# Set by cluster_scope(); the LangGraph node tasks spawned inside it inherit a copy of the
# context, so every tool call in one cluster shares this session and this cache.
_ACTIVE_SESSION: ContextVar = ContextVar("github_mcp_session", default=None)
_ACTIVE_FILE_CACHE: ContextVar = ContextVar("github_mcp_file_cache", default=None)


class DirListing(BaseModel):
    """A directory at `path` and the repo-relative paths it contains."""

    path: str
    entries: list[str]


class FileContent(BaseModel):
    """A single file at `path` and its raw text."""

    path: str
    text: str


class GitHubMCPManager:
    def __init__(self):
        client = MultiServerMCPClient(
            {
                "github": {
                    "transport": "http",
                    "url": "https://api.githubcopilot.com/mcp/",
                    "headers": {
                        "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
                        "X-MCP-Toolsets": "repos,code_search,issues,pull_requests,git",  # Edit for specific toolsets
                    },
                }
            }
        )
        self.client = client

    @asynccontextmanager
    async def cluster_scope(self):
        """Hold one MCP session and one file cache for the whole of one cluster's run.

        Without this, every method opened its own session, so each file fetch paid a full
        HTTP connect plus MCP `initialize` handshake — ~150 handshakes per compliance run.
        """
        async with self.client.session("github") as session:
            session_token = _ACTIVE_SESSION.set(session)
            cache_token = _ACTIVE_FILE_CACHE.set({})
            try:
                yield session
            finally:
                _ACTIVE_FILE_CACHE.reset(cache_token)
                _ACTIVE_SESSION.reset(session_token)

    @asynccontextmanager
    async def _session(self):
        """Reuse the scope's session when one is open, otherwise fall back to a one-shot."""
        session = _ACTIVE_SESSION.get()
        if session is not None:
            yield session
            return
        async with self.client.session("github") as session:
            yield session

    async def _call_tool(self, tool_name: str, payload: dict):
        session = _ACTIVE_SESSION.get()
        if session is not None:
            try:
                return await session.call_tool(tool_name, payload)
            except Exception:
                # A pooled session that died mid-cluster must not poison the calls after it.
                _ACTIVE_SESSION.set(None)
        async with self.client.session("github") as fresh_session:
            return await fresh_session.call_tool(tool_name, payload)

    def _cache_get(self, owner: str, repo: str, path: str):
        file_cache = _ACTIVE_FILE_CACHE.get()
        if file_cache is None:
            return None
        return file_cache.get((owner, repo, path))

    def _cache_put(self, owner: str, repo: str, path: str, result) -> None:
        file_cache = _ACTIVE_FILE_CACHE.get()
        if file_cache is not None:
            file_cache[(owner, repo, path)] = result

    @staticmethod
    def _render(result: "DirListing | FileContent") -> str:
        """The one place fetched repo bytes become model-facing text, so the wrap is unconditional.

        The cache stores raw typed results, never rendered strings: cache hits and misses
        therefore converge here and no path can serve repository content undelimited.
        """
        if isinstance(result, DirListing):
            listing = "\n".join(result.entries) or "(empty directory)"
            return wrap_untrusted(DIRECTORY_TAG, result.path or "/", listing)
        return wrap_untrusted(FILE_TAG, result.path, result.text)

    def cached_file_content(self, owner: str, repo: str, path: str) -> str | None:
        """Wrapped content for a path already fetched in this scope, or None. Never hits the network."""
        result = self._cache_get(owner, repo, path)
        return None if result is None else self._render(result)

    async def get_tools(self):
        async with self._session() as github_session:
            tools = await github_session.list_tools()

        return tools.tools

    async def get_input_schema(self, tool_name: str):
        async with self._session() as github_session:
            tools = await github_session.list_tools()
            tool = next((t for t in tools.tools if t.name == tool_name), None)
            if tool:
                return tool.inputSchema
            else:
                print(f"Tool '{tool_name}' not found.")
                return None

    async def search_codebase(self, query: str):
        """Search the codebase using GitHub's code search tool. The query should be in the format:
        "search_term repo:owner/repo_name
        """
        try:
            result = await self._call_tool("search_code", {"query": query})
            if not result.content:
                return []

            content_text = result.content[0].text
            try:
                data = json.loads(content_text)
            except json.JSONDecodeError:
                return []

            return [item["path"] for item in data.get("items", [])]
        except Exception as e:
            print(f"Error during code search: {e}")
            return []

    @staticmethod
    def _normalize_fetch_result(path: str, result) -> "DirListing | FileContent":
        if len(result.content) > 1 and result.content[1]:
            return FileContent(path=path, text=result.content[1].resource.text)

        content_text = result.content[0].text
        try:
            data = json.loads(content_text)
        except json.JSONDecodeError:
            return FileContent(path=path, text=content_text)

        if not isinstance(data, list):
            return FileContent(path=path, text=content_text)

        entries = []
        for item in data:
            entry = item.get("path") or item.get("name")
            if not entry:
                continue
            # Trailing slash preserves the file/dir distinction the old dict carried.
            entries.append(f"{entry}/" if item.get("type") == "dir" else entry)
        return DirListing(path=path, entries=entries)

    async def fetch_path(
        self, owner: str, repo: str, path: str
    ) -> DirListing | FileContent:
        """Fetch a repo path, normalized to exactly one of DirListing or FileContent."""
        cached = self._cache_get(owner, repo, path)
        if cached is not None:
            return cached

        result = await self._call_tool(
            "get_file_contents", {"owner": owner, "repo": repo, "path": path}
        )
        normalized = self._normalize_fetch_result(path, result)
        self._cache_put(owner, repo, path, normalized)
        return normalized

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Retrieve the content of a file from a GitHub repository.

        If path is a folder, returns the list of paths it contains instead.
        """
        # Model-facing boundary: fetch_path stays typed and verbatim for programmatic
        # callers, and only the string that reaches the LLM is capped and delimited.
        return self._render(await self.fetch_path(owner=owner, repo=repo, path=path))

    async def get_repository_tree(
        self,
        owner: str,
        repo: str,
        tree_sha: str | None = None,
        recursive: bool = False,
        path_filter: str | None = None,
    ) -> str:
        """Retrieve the repository tree for a ref or tree SHA."""
        payload = {
            "owner": owner,
            "repo": repo,
            "recursive": recursive,
        }
        if tree_sha:
            payload["tree_sha"] = tree_sha
        if path_filter:
            payload["path_filter"] = path_filter

        scope = path_filter or tree_sha or "/"
        result = await self._call_tool("get_repository_tree", payload)
        if not result.content:
            return wrap_untrusted(TREE_TAG, scope, "(no entries)")

        content_text = result.content[0].text
        try:
            data = json.loads(content_text)
        except json.JSONDecodeError:
            data = content_text

        entries = []
        if isinstance(data, dict) and "tree" in data:
            for item in data["tree"]:
                entries.append(f"{item.get('path')} ({item.get('type')})")

        # Paths are repo-authored strings, so the tree is delimited and capped too.
        return wrap_untrusted(TREE_TAG, scope, "\n".join(entries) or "(no entries)")


@cache
def get_github_mcp_manager() -> GitHubMCPManager:
    """Lazy singleton so importing the graph does not read credentials or build clients."""
    return GitHubMCPManager()
