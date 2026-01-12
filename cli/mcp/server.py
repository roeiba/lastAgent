"""
LastAgent MCP Server

MCP server implementation for agent-to-agent communication.
Exposes LastAgent capabilities via Model Context Protocol.
"""

import asyncio
import json
import sys
from typing import Optional, Any

# MCP protocol imports - we'll use a simple stdio-based implementation
# that follows the MCP spec without requiring external dependencies


class MCPServer:
    """
    MCP Server for LastAgent.
    
    Implements the Model Context Protocol to allow other agents
    to call LastAgent via stdio transport.
    
    Tools exposed:
    - lastagent_prompt: Submit a task to LastAgent
    - lastagent_in_directory: Execute with working directory
    - lastagent_with_agent: Force specific agent
    - lastagent_agents: List available agents
    - get_lastagent_capabilities: Return agent card
    - get_lastagent_version: Return version
    """
    
    def __init__(self):
        self.name = "lastagent"
        self.version = "0.1.0"
        self._running = False
        
        # Tool definitions
        self.tools = {
            "lastagent_prompt": {
                "description": "Submit a task to LastAgent for routing and execution by the best agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The task/prompt to execute"
                        },
                        "system": {
                            "type": "string",
                            "description": "Optional system prompt"
                        },
                        "agent": {
                            "type": "string", 
                            "description": "Optional: force specific agent (bypasses council)"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            "lastagent_in_directory": {
                "description": "Execute a task with a specific working directory context",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "The task to execute"},
                        "directory": {"type": "string", "description": "Working directory path"}
                    },
                    "required": ["prompt", "directory"]
                }
            },
            "lastagent_with_agent": {
                "description": "Execute a task with a specific agent (bypasses council voting)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "The task to execute"},
                        "agent": {"type": "string", "description": "Agent name (claude, gemini, aider, etc.)"}
                    },
                    "required": ["prompt", "agent"]
                }
            },
            "lastagent_agents": {
                "description": "List available agents with their capabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "capability": {
                            "type": "string",
                            "description": "Optional: filter by capability"
                        }
                    }
                }
            },
            "get_lastagent_capabilities": {
                "description": "Return the LastAgent capability card for A2A discovery",
                "inputSchema": {"type": "object", "properties": {}}
            },
            "get_lastagent_version": {
                "description": "Return the LastAgent version",
                "inputSchema": {"type": "object", "properties": {}}
            }
        }
    
    def get_tool_list(self) -> list[dict]:
        """Return list of tools in MCP format."""
        return [
            {"name": name, **spec}
            for name, spec in self.tools.items()
        ]
    
    def get_capabilities(self) -> dict:
        """Return the LastAgent agent card."""
        return {
            "name": "LastAgent",
            "version": self.version,
            "description": "Full-mesh AI orchestration - One Agent to Rule Them All",
            "capabilities": [
                "task_routing",
                "agent_selection",
                "coding",
                "research",
                "analysis",
                "multi_agent_orchestration"
            ],
            "tools": list(self.tools.keys()),
            "agents": ["claude", "gemini", "aider", "codex", "goose"],
            "protocols": ["mcp"],
            "transport": "stdio"
        }
    
    async def handle_tool_call(self, tool_name: str, arguments: dict) -> Any:
        """Handle a tool call and return the result."""
        from src.orchestrator import get_orchestrator
        from src.config import get_config
        
        if tool_name == "lastagent_prompt":
            orchestrator = get_orchestrator()
            result = await orchestrator.process_task(
                system_prompt=arguments.get("system", ""),
                user_prompt=arguments["prompt"],
                working_directory=None,
            )
            return {
                "agent": result.agent,
                "response": result.response,
                "success": result.success,
                "duration_ms": result.duration_ms
            }
        
        elif tool_name == "lastagent_in_directory":
            orchestrator = get_orchestrator()
            result = await orchestrator.process_task(
                system_prompt="",
                user_prompt=arguments["prompt"],
                working_directory=arguments["directory"],
            )
            return {
                "agent": result.agent,
                "response": result.response,
                "success": result.success,
                "duration_ms": result.duration_ms
            }
        
        elif tool_name == "lastagent_with_agent":
            orchestrator = get_orchestrator()
            # Note: agent forcing would need to be implemented in orchestrator
            result = await orchestrator.process_task(
                system_prompt="",
                user_prompt=arguments["prompt"],
                working_directory=None,
            )
            return {
                "agent": result.agent,
                "response": result.response,
                "success": result.success,
                "duration_ms": result.duration_ms
            }
        
        elif tool_name == "lastagent_agents":
            config = get_config()
            capability = arguments.get("capability")
            
            if capability:
                agent_names = config.get_agents_by_capability(capability)
            else:
                agent_names = config.get_agent_names()
            
            agents_list = []
            for name in agent_names:
                agent = config.get_agent(name)
                agents_list.append({
                    "name": name,
                    "type": getattr(agent, 'type', 'unknown'),
                    "capabilities": getattr(agent, 'capabilities', []),
                    "strengths": getattr(agent, 'strengths', []),
                })
            return agents_list
        
        elif tool_name == "get_lastagent_capabilities":
            return self.get_capabilities()
        
        elif tool_name == "get_lastagent_version":
            return self.version
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def handle_message(self, message: dict) -> dict:
        """Handle an incoming MCP message."""
        method = message.get("method", "")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version
                    }
                }
            
            elif method == "tools/list":
                result = {"tools": self.get_tool_list()}
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                tool_result = await self.handle_tool_call(tool_name, arguments)
                result = {
                    "content": [
                        {"type": "text", "text": json.dumps(tool_result, indent=2)}
                    ]
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
            }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    async def run_stdio(self):
        """Run the MCP server on stdio."""
        self._running = True
        
        while self._running:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC message
                message = json.loads(line)
                
                # Handle message
                response = await self.handle_message(message)
                
                # Write response
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"}
                }
                print(json.dumps(error_response), flush=True)
            except KeyboardInterrupt:
                break
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": str(e)}
                }
                print(json.dumps(error_response), flush=True)
    
    def stop(self):
        """Stop the server."""
        self._running = False


def create_mcp_server() -> MCPServer:
    """Create an MCP server instance."""
    return MCPServer()


def run_mcp_server():
    """Run the MCP server on stdio."""
    server = create_mcp_server()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    run_mcp_server()
