"""
LastAgent CLI

Command-line interface for LastAgent operations.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="lastagent",
        description="LastAgent - Full-mesh AI orchestration system",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Submit a task to LastAgent")
    chat_parser.add_argument("prompt", help="The prompt/task to execute")
    chat_parser.add_argument(
        "-s", "--system", default="", help="System prompt"
    )
    chat_parser.add_argument(
        "-d", "--dir", default=None, help="Working directory"
    )
    chat_parser.add_argument(
        "-a", "--agent", default=None, help="Force specific agent"
    )
    
    # Agents command
    agents_parser = subparsers.add_parser("agents", help="List available agents")
    agents_parser.add_argument(
        "-c", "--capability", default=None, help="Filter by capability"
    )
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start the API server")
    server_parser.add_argument(
        "-p", "--port", type=int, default=8000, help="Port to run on"
    )
    server_parser.add_argument(
        "-h", "--host", default="0.0.0.0", help="Host to bind to"
    )
    
    # Workflow command
    workflow_parser = subparsers.add_parser("workflow", help="Run Agile TDD workflow")
    workflow_parser.add_argument(
        "phase",
        choices=["status", "plan", "implement", "integrate", "merge", "deploy", "present", "inputs", "all"],
        help="Workflow phase to run"
    )
    workflow_parser.add_argument(
        "-p", "--project", default=".", help="Project directory"
    )
    
    args = parser.parse_args()
    
    if args.command == "chat":
        asyncio.run(run_chat(args))
    elif args.command == "agents":
        run_agents(args)
    elif args.command == "server":
        run_server(args)
    elif args.command == "workflow":
        asyncio.run(run_workflow(args))
    else:
        parser.print_help()


async def run_chat(args):
    """Run a chat/task."""
    from src.orchestrator import get_orchestrator
    
    print(f"🤖 LastAgent processing task...")
    
    orchestrator = get_orchestrator()
    result = await orchestrator.process_task(
        system_prompt=args.system,
        user_prompt=args.prompt,
        working_directory=args.dir,
    )
    
    print(f"\n📋 Agent: {result.agent}")
    print(f"⏱️  Duration: {result.duration_ms}ms")
    print(f"✅ Success: {result.success}")
    print(f"\n{result.response}")


def run_agents(args):
    """List available agents."""
    from src.config import get_config
    
    config = get_config()
    
    if args.capability:
        agents = config.get_agents_by_capability(args.capability)
        print(f"Agents with '{args.capability}' capability:")
        for name in agents:
            print(f"  - {name}")
    else:
        print("Available agents:")
        for name in config.get_agent_names():
            agent = config.get_agent(name)
            print(f"  - {name}: {agent.strengths[0] if agent.strengths else ''}")


def run_server(args):
    """Run the API server."""
    import uvicorn
    
    print(f"🚀 Starting LastAgent API server on {args.host}:{args.port}")
    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=True,
    )


async def run_workflow(args):
    """Run Agile TDD workflow phase."""
    from src.workflow import get_workflow_runner
    
    runner = get_workflow_runner(args.project)
    
    if args.phase == "status":
        status = runner.get_status()
        print(f"📊 Workflow Status: {status}")
    elif args.phase == "all":
        print("🔄 Running full workflow cycle...")
        await runner.run_full_cycle()
    else:
        print(f"▶️  Running phase: {args.phase}")
        await runner.run_phase(args.phase)


if __name__ == "__main__":
    main()
