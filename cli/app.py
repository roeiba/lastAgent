"""
LastAgent CLI Application

Main Typer application with all commands registered.
This is the premium CLI experience matching claude-cli/gemini-cli aesthetics.
"""

import typer
from typing import Optional
from pathlib import Path

from cli.tui.console import console, print_logo, print_header, print_error

# ============================================================================
# Main Application
# ============================================================================

app = typer.Typer(
    name="lastagent",
    help="🤖 LastAgent - One Agent to Rule Them All\n\nFull-mesh AI orchestration that dynamically selects the best agent for any task.",
    add_completion=True,
    no_args_is_help=False,  # Allow running without args for REPL mode
    rich_markup_mode="rich",
)


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        from importlib.metadata import version as get_version
        try:
            ver = get_version("lastagent")
        except Exception:
            ver = "0.1.0-dev"
        console.print(f"[bold cyan]LastAgent[/] version [bold]{ver}[/]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt: Optional[str] = typer.Argument(
        None,
        help="Positional prompt for quick task execution (like gemini CLI).",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output.",
        envvar="NO_COLOR",
    ),
    yolo: bool = typer.Option(
        False,
        "--yolo",
        "-y",
        help="YOLO mode - auto-accept all actions without confirmation.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i", 
        help="Enter interactive mode after executing prompt.",
    ),
):
    """
    🤖 LastAgent - One Agent to Rule Them All
    
    Full-mesh AI orchestration that dynamically selects the best agent for any task.
    
    [bold cyan]Quick Start:[/]
    
        lastagent "Write a Python function"    # Positional prompt (like gemini)
        
        lastagent chat "Write a Python function"
        
        lastagent -y "Auto-execute this task"   # YOLO mode
        
        lastagent agents
        
        lastagent server
    
    [dim]Run 'lastagent' without arguments to enter interactive mode (Sprint 9.1).[/]
    """
    if no_color:
        console.no_color = True
    
    # If positional prompt provided, execute it directly (like gemini CLI)
    if prompt:
        import asyncio
        from cli.tui.spinners import AgentSpinner
        from cli.tui.console import print_agent_result, print_error
        
        if yolo:
            console.print("[dim]YOLO mode enabled. Auto-accepting all actions.[/]\n")
        
        async def run_quick_chat():
            from src.orchestrator import get_orchestrator
            
            with AgentSpinner("🗳️ Council voting...") as spinner:
                orchestrator = get_orchestrator()
                spinner.update("⚡ Executing task...")
                
                result = await orchestrator.process_task(
                    system_prompt="",
                    user_prompt=prompt,
                    working_directory=None,
                )
            
            print_agent_result(
                agent=result.agent,
                response=result.response,
                duration_ms=result.duration_ms,
                success=result.success,
                confidence=getattr(result, 'confidence', None),
                render_markdown=True,
            )
            
            if not result.success:
                raise typer.Exit(1)
        
        try:
            asyncio.run(run_quick_chat())
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/]")
            raise typer.Exit(130)
        except Exception as e:
            print_error(f"Error: {e}")
            raise typer.Exit(1)
        return
    
    # If no command and no prompt, enter REPL mode
    if ctx.invoked_subcommand is None:
        from cli.repl import run_repl
        run_repl()
        raise typer.Exit()


# ============================================================================
# Chat Command
# ============================================================================

@app.command()
def chat(
    prompt: str = typer.Argument(
        ...,
        help="The prompt/task to execute.",
    ),
    system: str = typer.Option(
        "",
        "--system", "-s",
        help="System prompt to prepend.",
    ),
    directory: Optional[Path] = typer.Option(
        None,
        "--dir", "-d",
        help="Working directory for the task.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    agent: Optional[str] = typer.Option(
        None,
        "--agent", "-a",
        help="Force a specific agent (bypasses council).",
    ),
    no_markdown: bool = typer.Option(
        False,
        "--no-markdown",
        help="Disable markdown rendering in output.",
    ),
    no_stream: bool = typer.Option(
        False,
        "--no-stream",
        help="Disable streaming output.",
    ),
):
    """
    Submit a task to LastAgent for processing.
    
    The LLM Council will vote to select the best agent, then execute
    the task and return the response.
    
    [bold cyan]Examples:[/]
    
        lastagent chat "Write a hello world in Python"
        
        lastagent chat "Refactor this file" -d ./src
        
        lastagent chat "Explain this code" -a claude
    """
    import asyncio
    from cli.tui.spinners import AgentSpinner
    from cli.tui.console import print_agent_result, print_success
    
    async def run_chat():
        # Import here to avoid circular imports
        from src.orchestrator import get_orchestrator
        
        with AgentSpinner("🗳️ Council voting...") as spinner:
            orchestrator = get_orchestrator()
            
            spinner.update("⚡ Executing task...")
            
            result = await orchestrator.process_task(
                system_prompt=system,
                user_prompt=prompt,
                working_directory=str(directory) if directory else None,
            )
        
        # Print result
        print_agent_result(
            agent=result.agent,
            response=result.response,
            duration_ms=result.duration_ms,
            success=result.success,
            confidence=getattr(result, 'confidence', None),
            render_markdown=not no_markdown,
        )
        
        if not result.success:
            raise typer.Exit(1)
    
    try:
        asyncio.run(run_chat())
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/]")
        raise typer.Exit(130)
    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(1)


# ============================================================================
# Agents Command
# ============================================================================

@app.command()
def agents(
    capability: Optional[str] = typer.Option(
        None,
        "--capability", "-c",
        help="Filter agents by capability.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
):
    """
    List available agents and their capabilities.
    
    [bold cyan]Examples:[/]
    
        lastagent agents
        
        lastagent agents -c coding
        
        lastagent agents --json
    """
    import json as json_lib
    from src.config import get_config
    from cli.tui.console import print_agents_table
    
    config = get_config()
    
    if capability:
        agent_names = config.get_agents_by_capability(capability)
        console.print(f"[dim]Agents with '{capability}' capability:[/]\n")
    else:
        agent_names = config.get_agent_names()
    
    agents_list = []
    for name in agent_names:
        agent = config.get_agent(name)
        agents_list.append({
            "name": name,
            "type": getattr(agent, 'type', 'unknown'),
            "strengths": getattr(agent, 'strengths', []),
            "available": True,  # Could check actual availability
        })
    
    if json_output:
        console.print(json_lib.dumps(agents_list, indent=2))
    else:
        print_agents_table(agents_list)


# ============================================================================
# Server Command
# ============================================================================

@app.command()
def server(
    port: int = typer.Option(
        8000,
        "--port", "-p",
        help="Port to run the server on.",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host", "-h",
        help="Host to bind to.",
    ),
    reload: bool = typer.Option(
        True,
        "--reload/--no-reload",
        help="Enable auto-reload for development.",
    ),
):
    """
    Start the LastAgent API server.
    
    Exposes an OpenAI-compatible REST API at /v1/chat/completions.
    
    [bold cyan]Examples:[/]
    
        lastagent server
        
        lastagent server -p 8080
        
        lastagent server --no-reload
    """
    import uvicorn
    
    print_header(
        f"Starting LastAgent API Server",
        f"http://{host}:{port}"
    )
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
    )


# ============================================================================
# Workflow Command
# ============================================================================

@app.command()
def workflow(
    phase: str = typer.Argument(
        ...,
        help="Workflow phase to run: status, plan, implement, integrate, merge, deploy, present, inputs, all",
    ),
    project: Path = typer.Option(
        Path("."),
        "--project", "-p",
        help="Project directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
):
    """
    Run Agile TDD workflow phases.
    
    [bold cyan]Examples:[/]
    
        lastagent workflow status
        
        lastagent workflow plan -p ./myproject
        
        lastagent workflow all
    """
    import asyncio
    from cli.tui.console import print_info
    
    valid_phases = ["status", "plan", "implement", "integrate", "merge", "deploy", "present", "inputs", "all"]
    
    if phase not in valid_phases:
        print_error(f"Invalid phase '{phase}'. Must be one of: {', '.join(valid_phases)}")
        raise typer.Exit(1)
    
    async def run_workflow():
        from src.workflow import get_workflow_runner
        
        runner = get_workflow_runner(str(project))
        
        if phase == "status":
            status = runner.get_status()
            console.print(f"[bold]📊 Workflow Status:[/] {status}")
        elif phase == "all":
            print_info("Running full workflow cycle...")
            await runner.run_full_cycle()
        else:
            print_info(f"Running phase: {phase}")
            await runner.run_phase(phase)
    
    try:
        asyncio.run(run_workflow())
    except Exception as e:
        print_error(f"Workflow error: {e}")
        raise typer.Exit(1)


# ============================================================================
# Placeholder Commands (Future Sprints)
# ============================================================================

@app.command(hidden=True)
def config():
    """Configuration management (Sprint 9.1)."""
    console.print("[dim]Config management coming in Sprint 9.1[/]")


@app.command()
def mcp():
    """
    Start LastAgent as an MCP server.
    
    Runs on stdio transport for agent-to-agent communication.
    Other agents can call LastAgent via Model Context Protocol.
    
    [bold cyan]Tools Exposed:[/]
    
        lastagent_prompt       - Submit a task for routing
        lastagent_agents       - List available agents
        get_lastagent_capabilities - Get agent card
    
    [bold cyan]Usage:[/]
    
        # Start MCP server (in MCP client config)
        lastagent mcp
    """
    from cli.tui.console import print_info
    from cli.mcp import run_mcp_server
    
    print_info("Starting LastAgent MCP server on stdio...")
    print_info("Waiting for MCP client connection...")
    
    try:
        run_mcp_server()
    except KeyboardInterrupt:
        console.print("\n[dim]MCP server stopped.[/]")


@app.command(hidden=True)
def init():
    """Installation wizard (Sprint 9.3)."""
    console.print("[dim]Installation wizard coming in Sprint 9.3[/]")


if __name__ == "__main__":
    app()
