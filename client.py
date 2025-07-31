import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI 
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = OpenAI()  

    async def connect_to_server(self, server_script_path: str):
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None
        )

        stdio = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(*stdio))
        await self.session.initialize()

        tools_response = await self.session.list_tools()
        self.tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in tools_response.tools]

        print("Connected to MCP server with tools:", [t["function"]["name"] for t in self.tools])

    async def process_query(self, query: str):
        messages = [{"role": "user", "content": query}]
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        content = response.choices[0].message
        messages.append(content)

        if content.tool_calls:
            for tool_call in content.tool_calls:

                parsed_args = json.loads(tool_call.function.arguments)
                result = await self.session.call_tool(
                    tool_call.function.name,
                    parsed_args
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.content
                })

                # Send result back to GPT
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                content = response.choices[0].message
                print("\nResponse:\n", content.content)
        else:
            print("\nResponse:\n", content.content)

    async def chat_loop(self):
        print("Type a query or 'quit':")
        while True:
            q = input("Query: ").strip()
            if q.lower() == "quit":
                break
            await self.process_query(q)

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python client.py path/to/server.py")
        return
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
