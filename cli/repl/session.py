"""
LastAgent REPL Session Manager

Interactive shell with command history, slash commands, and multi-line input.
Matches the UX of gemini CLI interactive mode.
"""

import asyncio
import os
from pathlib import Path
from typing import Optional, Callable, Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown

from cli.tui.console import (
    console,
    print_logo,
    print_header,
    print_success,
    print_error,
    print_info,
    print_agent_result,
    print_agents_table,
)
from cli.tui.spinners import AgentSpinner


# ============================================================================
# REPL Style
# ============================================================================

REPL_STYLE = Style.from_dict({
    'prompt': 'bold cyan',
    'prompt.agent': 'bold magenta',
    'continuation': 'dim cyan',
})


# ============================================================================
# Slash Commands
# ============================================================================

SLASH_COMMANDS = {
    '/help': 'Show available commands',
    '/agents': 'List available agents',
    '/agent': 'Switch default agent (e.g., /agent claude)',
    '/clear': 'Clear the screen',
    '/history': 'Show command history',
    '/config': 'Show current configuration',
    '/exit': 'Exit interactive mode',
    '/quit': 'Exit interactive mode (alias)',
}


# ============================================================================
# REPL Session
# ============================================================================

class REPLSession:
    """
    Interactive REPL session for LastAgent.
    
    Features:
    - Command history with persistence
    - Slash commands for session control
    - Multi-line input support
    - Agent switching
    """
    
    def __init__(
        self,
        history_file: Optional[Path] = None,
        default_agent: Optional[str] = None,
    ):
        # History file in ~/.lastagent/
        if history_file is None:
            history_dir = Path.home() / ".lastagent"
            history_dir.mkdir(exist_ok=True)
            history_file = history_dir / "history"
        
        self.history_file = history_file
        self.default_agent = default_agent
        self.current_agent: Optional[str] = default_agent
        self.console = console
        self._running = False
        
        # Create prompt session with history
        self.session = PromptSession(
            history=FileHistory(str(self.history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            style=REPL_STYLE,
            multiline=False,
            enable_history_search=True,
        )
    
    def _get_prompt(self) -> HTML:
        """Generate the prompt string."""
        agent_part = f" [{self.current_agent}]" if self.current_agent else ""
        return HTML(f'<prompt>🤖 lastagent</prompt><prompt.agent>{agent_part}</prompt.agent><prompt>> </prompt>')
    
    async def _handle_slash_command(self, command: str) -> bool:
        """
        Handle slash commands.
        
        Returns True if the command was handled, False otherwise.
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in ('/exit', '/quit'):
            self._running = False
            return True
        
        elif cmd == '/help':
            self.console.print("\n[bold cyan]Available Commands:[/]\n")
            for slash_cmd, desc in SLASH_COMMANDS.items():
                self.console.print(f"  [bold]{slash_cmd:12}[/] {desc}")
            self.console.print("\n[dim]Type any text to send as a prompt to LastAgent.[/]\n")
            return True
        
        elif cmd == '/agents':
            from src.config import get_config
            config = get_config()
            agents_list = []
            for name in config.get_agent_names():
                agent = config.get_agent(name)
                agents_list.append({
                    "name": name,
                    "type": getattr(agent, 'type', 'unknown'),
                    "strengths": getattr(agent, 'strengths', []),
                    "available": True,
                })
            self.console.print()
            print_agents_table(agents_list)
            self.console.print()
            return True
        
        elif cmd == '/agent':
            if args:
                from src.config import get_config
                config = get_config()
                if args in config.get_agent_names():
                    self.current_agent = args
                    print_success(f"Switched to agent: {args}")
                else:
                    print_error(f"Unknown agent: {args}")
                    print_info(f"Available: {', '.join(config.get_agent_names())}")
            else:
                if self.current_agent:
                    print_info(f"Current agent: {self.current_agent}")
                else:
                    print_info("No agent selected (council will choose)")
            return True
        
        elif cmd == '/clear':
            os.system('clear' if os.name != 'nt' else 'cls')
            print_logo()
            return True
        
        elif cmd == '/history':
            self.console.print("\n[bold cyan]Recent History:[/]\n")
            history_items = list(self.session.history.get_strings())[-10:]
            for i, item in enumerate(history_items, 1):
                self.console.print(f"  [dim]{i:2}.[/] {item[:60]}{'...' if len(item) > 60 else ''}")
            self.console.print()
            return True
        
        elif cmd == '/config':
            self.console.print("\n[bold cyan]Current Configuration:[/]\n")
            self.console.print(f"  [bold]Agent:[/] {self.current_agent or 'auto (council decides)'}")
            self.console.print(f"  [bold]History:[/] {self.history_file}")
            self.console.print()
            return True
        
        return False
    
    async def _execute_prompt(self, prompt: str):
        """Execute a prompt with LastAgent."""
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
        self.console.print()
    
    async def run(self):
        """Run the interactive REPL loop."""
        print_logo()
        self.console.print("[dim]Type /help for commands, /exit to quit.[/]\n")
        
        self._running = True
        
        while self._running:
            try:
                # Get input from user
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.session.prompt(self._get_prompt())
                )
                
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # Handle slash commands
                if user_input.startswith('/'):
                    handled = await self._handle_slash_command(user_input)
                    if handled:
                        continue
                
                # Execute as prompt
                await self._execute_prompt(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[dim]Interrupted. Type /exit to quit.[/]")
                continue
            except EOFError:
                # Ctrl+D
                self._running = False
                break
            except Exception as e:
                print_error(f"Error: {e}")
        
        self.console.print("\n[bold cyan]Goodbye! 👋[/]\n")


# ============================================================================
# Entry Point
# ============================================================================

def run_repl(
    default_agent: Optional[str] = None,
    history_file: Optional[Path] = None,
):
    """
    Run the LastAgent interactive REPL.
    
    Args:
        default_agent: Optional default agent to use
        history_file: Optional custom history file path
    """
    session = REPLSession(
        history_file=history_file,
        default_agent=default_agent,
    )
    asyncio.run(session.run())


if __name__ == "__main__":
    run_repl()
