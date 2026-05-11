import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()


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

            async with self.client.session("github") as github_session:
                result = await github_session.call_tool("search_code", {"query": query})
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
        async with self.client.session("github") as github_session:
            result = await github_session.call_tool(
                "get_file_contents", {"owner": owner, "repo": repo, "path": path}
            )
            if len(result.content) > 1 and result.content[1]:
                return f"{path}\n\n{result.content[1].resource.text}"
            else:
                content_text = result.content[0].text
                try:
                    data = json.loads(content_text)
                except json.JSONDecodeError:
                    return f"{path}\n\n{content_text}"

                if not isinstance(data, list):
                    return data

                results_array = []
                for item in data:
                    results_array.append(
                        {
                            "name": item.get("name"),
                            "entry_type": item.get("type"),
                            "path": item.get("path"),
                        }
                    )
                return results_array

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

        async with self.client.session("github") as github_session:
            result = await github_session.call_tool("get_repository_tree", payload)
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
