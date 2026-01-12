"""
LastAgent MCP Package

MCP (Model Context Protocol) server for agent-to-agent communication.
Allows other agents to call LastAgent via MCP.
"""

from cli.mcp.server import create_mcp_server, run_mcp_server

__all__ = ["create_mcp_server", "run_mcp_server"]
