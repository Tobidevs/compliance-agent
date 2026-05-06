# from .utils.github_mcp import GitHubMCPManager
# from dotenv import load_dotenv
# import os
# load_dotenv()
# import asyncio

# mcp = GitHubMCPManager(token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"))

# async def main():
#     session = await mcp.connect()
#     results = await session.call_tool(
#     "search_repositories", 
#     {
#         "owner": "acmuta",
#         "repo": "mavresume"
        
#     }
#     )
#     print(results.content[0].text)
    
#     await mcp.disconnect()

# if __name__ == "__main__":
#     asyncio.run(main())

from http import client
import json
import os
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from dotenv import load_dotenv

from .utils.github_mcp import GitHubMCPManager
from .utils.policy_rag_service import PolicyRAGService

load_dotenv()

async def main():
    # client = MultiServerMCPClient(
    #     {
    #         "github": {
    #             "transport": "http",
    #             "url": "https://api.githubcopilot.com/mcp/",
    #             "headers": {
    #                 "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
    #                 # Enable correct toolsets
    #                 "X-MCP-Toolsets": "repos,code_search"
    #             },
    #         }
    #     }
    # )

    # async with client.session("github") as github_session:
    #     tools = await github_session.list_tools()

    #     result = await github_session.call_tool(
    #         "search_code",
    #         {"query": "authentication repo:acmuta/mavresume"}
    #     )

    #     raw = []

    #     for block in result.content:
    #         text = block.text

    #         for line in text.split("\n"):
    #             if "/" in line and "." in line:  # naive path detection
    #                 raw.append(line.strip())

    #     data = json.loads(raw[0])
    #     paths = [item["path"] for item in data["items"]]
        
       
        
        
    #     response = await github_session.call_tool(
    #     "get_file_contents",
    #     {
    #         "owner": "acmuta",
    #         "repo": "mavresume",
    #         "path": paths[0]
    #     }
    #     )

    #     print(response.content[1].resource.text)
        

        # print(result.content[0].text)
        
    github_mcp_manager = GitHubMCPManager()
    file_paths = await github_mcp_manager.get_file_content(
        repo="mavresume",
        owner="acmuta",
        path="lib"
    )
    print(file_paths)
    



asyncio.run(main())