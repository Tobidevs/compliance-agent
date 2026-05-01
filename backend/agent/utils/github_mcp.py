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
                        "X-MCP-Toolsets": "repos,code_search",  # Edit for specific toolsets
                    },
                }
            }
        )
        self.client = client

    async def get_tools(self):
        async with self.client.session("github") as github_session:
            tools = await github_session.list_tools()

        print("Available GitHub MCP Tools:")
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
    @tool
    async def search_codebase(self, query: str):
        """ Search the codebase using GitHub's code search tool. The query should be in the format:
        "search_term repo:owner/repo_name
        """
        async with self.client.session("github") as github_session:
            result = await github_session.call_tool("search_code", {"query": query})
            raw = []
            for block in result.content:
                text = block.text
                for line in text.split("\n"):
                    if "/" in line and "." in line:
                        raw.append(line.strip())

            data = json.loads(raw[0])
            return [item["path"] for item in data["items"]]

    @tool
    async def get_file_content(self, owner: str, repo: str, path: str):
        """ Retrieve the content of a file from a GitHub repository. """
        async with self.client.session("github") as github_session:
            result = await github_session.call_tool(
                "get_file_content", {"owner": owner, "repo": repo, "path": path}
            )
            return result.content[0].text
