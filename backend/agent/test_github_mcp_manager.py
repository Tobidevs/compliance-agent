import asyncio
import json
import unittest
from types import SimpleNamespace

from .utils.github_mcp import (
    GitHubMCPManager,
    GitHubMCPRateLimitError,
    is_github_mcp_rate_limit_error,
    is_github_mcp_retryable_error,
)


class CountingGitHubMCPManager(GitHubMCPManager):
    def __init__(self):
        self.call_count = 0

    async def _call_github_tool_without_lock(self, tool_name: str, payload: dict):
        self.call_count += 1
        await asyncio.sleep(0.01)
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    text=json.dumps(
                        [{"name": "app.py", "type": "file", "path": "app.py"}]
                    )
                )
            ]
        )


class AlwaysRateLimitedSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def call_tool(self, tool_name: str, payload: dict):
        raise Exception("429 too many requests")


class AlwaysRateLimitedClient:
    def session(self, name: str):
        return AlwaysRateLimitedSession()


class GitHubMCPManagerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        GitHubMCPManager._cache = {}
        GitHubMCPManager._semaphore = asyncio.Semaphore(1)
        GitHubMCPManager._min_interval_seconds = 0
        GitHubMCPManager._max_retries = 0

    def test_rate_limit_detection(self):
        self.assertTrue(is_github_mcp_rate_limit_error("429 too many requests"))
        self.assertTrue(is_github_mcp_rate_limit_error("secondary rate limit"))
        self.assertTrue(is_github_mcp_retryable_error("503 temporarily unavailable"))
        self.assertFalse(is_github_mcp_retryable_error("repository not found"))

    async def test_concurrent_duplicate_file_requests_use_one_mcp_call(self):
        manager = CountingGitHubMCPManager()

        first, second = await asyncio.gather(
            manager.get_file_content("owner", "repo", "app.py"),
            manager.get_file_content("owner", "repo", "app.py"),
        )

        self.assertEqual(first, second)
        self.assertEqual(manager.call_count, 1)

    async def test_rate_limit_exhaustion_raises_specific_error(self):
        manager = GitHubMCPManager()
        manager.client = AlwaysRateLimitedClient()

        with self.assertRaises(GitHubMCPRateLimitError):
            await manager._call_github_tool("get_file_contents", {})


if __name__ == "__main__":
    unittest.main()
