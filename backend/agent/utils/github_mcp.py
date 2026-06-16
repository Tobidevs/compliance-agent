import asyncio
import json
import os
import random
import time
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()


class GitHubMCPRateLimitError(Exception):
    """Raised when GitHub MCP remains rate-limited after retries."""


class GitHubMCPTransientError(Exception):
    """Raised when GitHub MCP returns a retryable transient failure."""


def is_github_mcp_rate_limit_error(error: Exception | str) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "rate limit",
            "too many requests",
            "429",
            "secondary rate limit",
            "quota",
        )
    )


def is_github_mcp_retryable_error(error: Exception | str) -> bool:
    message = str(error).lower()
    return is_github_mcp_rate_limit_error(message) or any(
        marker in message
        for marker in (
            "timed out",
            "timeout",
            "temporarily unavailable",
            "connection reset",
            "connection aborted",
            "502",
            "503",
            "504",
        )
    )


def format_github_mcp_tool_error(error: Exception) -> str:
    if is_github_mcp_rate_limit_error(error):
        return (
            "GitHub MCP rate limit reached after retries. Stop searching this "
            "control and call conclude_evidence with no_evidence_found=true. "
            f"Tool error: {error}"
        )

    return (
        "GitHub MCP tool failed. Stop searching this control if no other "
        "evidence is already available, then call conclude_evidence. "
        f"Tool error: {error}"
    )


class GitHubMCPManager:
    _max_concurrent = max(1, int(os.getenv("GITHUB_MCP_MAX_CONCURRENT", "1")))
    _min_interval_seconds = max(
        0.0, float(os.getenv("GITHUB_MCP_MIN_INTERVAL_SECONDS", "1.0"))
    )
    _max_retries = max(0, int(os.getenv("GITHUB_MCP_MAX_RETRIES", "3")))
    _backoff_base_seconds = max(
        0.1, float(os.getenv("GITHUB_MCP_BACKOFF_BASE_SECONDS", "2.0"))
    )
    _semaphore = asyncio.Semaphore(_max_concurrent)
    _rate_lock = asyncio.Lock()
    _cache_lock = asyncio.Lock()
    _last_call_started_at = 0.0
    _cache: dict[tuple, object] = {}

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

    @classmethod
    async def _throttle(cls):
        async with cls._rate_lock:
            now = time.monotonic()
            elapsed = now - cls._last_call_started_at
            if elapsed < cls._min_interval_seconds:
                await asyncio.sleep(cls._min_interval_seconds - elapsed)
            cls._last_call_started_at = time.monotonic()

    @classmethod
    async def _get_cached(cls, key: tuple):
        async with cls._cache_lock:
            return cls._cache.get(key)

    @classmethod
    async def _set_cached(cls, key: tuple, value):
        async with cls._cache_lock:
            cls._cache[key] = value

    async def get_tools(self):
        async with self.client.session("github") as github_session:
            tools = await github_session.list_tools()

        return tools.tools

    async def get_input_schema(self, tool_name: str):
        async with self.client.session("github") as github_session:
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

            result = await self._call_github_tool("search_code", {"query": query})
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

    async def get_file_content(self, owner: str, repo: str, path: str):
        """Retrieve the content of a file from a GitHub repository."""
        cache_key = ("get_file_contents", owner, repo, path)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        async with self._semaphore:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                return cached

            result = await self._call_github_tool_without_lock(
                "get_file_contents", {"owner": owner, "repo": repo, "path": path}
            )

        parsed_result = self._parse_file_content_result(path, result)
        await self._set_cached(cache_key, parsed_result)
        return parsed_result

    async def _call_github_tool_without_lock(self, tool_name: str, payload: dict):
        retry_count = self._max_retries + 1
        last_error: Exception | None = None

        for attempt in range(retry_count):
            try:
                await self._throttle()
                async with self.client.session("github") as github_session:
                    return await github_session.call_tool(tool_name, payload)
            except Exception as error:
                last_error = error
                if attempt >= self._max_retries or not is_github_mcp_retryable_error(
                    error
                ):
                    break

                backoff = self._backoff_base_seconds * (2**attempt)
                jitter = random.uniform(0, min(1.0, backoff * 0.25))
                await asyncio.sleep(backoff + jitter)

        if last_error and is_github_mcp_rate_limit_error(last_error):
            raise GitHubMCPRateLimitError(str(last_error)) from last_error
        if last_error and is_github_mcp_retryable_error(last_error):
            raise GitHubMCPTransientError(str(last_error)) from last_error
        if last_error:
            raise last_error
        raise GitHubMCPTransientError("GitHub MCP call failed without an error.")

    def _parse_file_content_result(self, path: str, result):
        if len(result.content) > 1 and result.content[1]:
            return f"{path}\n\n{result.content[1].resource.text}"

        content_text = result.content[0].text
        try:
            data = json.loads(content_text)
        except json.JSONDecodeError:
            return f"{path}\n\n{content_text}"

        if not isinstance(data, list):
            return data

        return [
            {
                "name": item.get("name"),
                "entry_type": item.get("type"),
                "path": item.get("path"),
            }
            for item in data
        ]

    async def get_repository_tree(
        self,
        owner: str,
        repo: str,
        tree_sha: str | None = None,
        recursive: bool = False,
        path_filter: str | None = None,
    ):
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

        cache_key = (
            "get_repository_tree",
            owner,
            repo,
            tree_sha,
            recursive,
            path_filter,
        )
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        async with self._semaphore:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                return cached

            result = await self._call_github_tool_without_lock(
                "get_repository_tree", payload
            )

        results_array = self._parse_repository_tree_result(result)
        await self._set_cached(cache_key, results_array)
        return results_array

    def _parse_repository_tree_result(self, result):
        if not result.content:
            return []

        content_text = result.content[0].text
        try:
            data = json.loads(content_text)
        except json.JSONDecodeError:
            data = content_text

        results_array = []
        if isinstance(data, dict) and "tree" in data:
            for item in data["tree"]:
                results_array.append(
                    {
                        "path": item.get("path"),
                        "type": item.get("type"),
                    }
                )

        return results_array

    async def _call_github_tool(self, tool_name: str, payload: dict):
        async with self._semaphore:
            return await self._call_github_tool_without_lock(tool_name, payload)
