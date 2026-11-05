import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
HEAR = Path(__file__).resolve().parent

async def main():
    server = StdioServerParameters(command="python", args=[str(HEAR / "mcp_server.py")])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            for t in tools.tools:
                print("工具:", t.name, "-", t.description)
            res = await session.call_tool("add", {"a" : 1, "b" : 2})
            print("结果", res.content[0].text)
            search = await session.call_tool("search_doc", {"query" : "RAG 检索失败率"})
            print("结果:", search.content[0].text)
asyncio.run(main())