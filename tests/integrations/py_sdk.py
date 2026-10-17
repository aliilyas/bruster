#!/usr/bin/env python3
"""Drives bruster through the official MCP Python SDK. Usage: py_sdk.py <bruster> [args...]"""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def is_error(result):
    """Accept the current SDK field and older snake_case wrappers."""
    if hasattr(result, 'isError'):
        return result.isError
    return result.is_error


async def main(command, args):
    params = StdioServerParameters(command=command, args=args)
    async with stdio_client(params, errlog=open('/dev/null', 'w')) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            assert len(tools) > 30, len(tools)
            nav = await s.call_tool('navigate', {'url': 'https://example.com/'})
            assert 'example.com' in nav.content[0].text, nav
            found = await s.call_tool('find', {'text': 'Learn more'})
            assert 'link' in found.content[0].text, found
            tabs = await s.call_tool('new_tab', {'url': 'https://example.com/'})
            assert '"tab"' in tabs.content[0].text, tabs
            bad = await s.call_tool('eval', {'expression': 'throw new Error("boom")'})
            assert is_error(bad) and 'boom' in bad.content[0].text, bad
            print('PASS py-sdk', len(tools), 'tools')


asyncio.run(main(sys.argv[1], sys.argv[2:]))
