"""
LastAgent Console Module

Rich console configuration and styled output helpers for the CLI.
Provides consistent branding and visual feedback matching claude-cli/gemini-cli aesthetics.
"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.style import Style
from rich.theme import Theme

# ============================================================================
# Brand Colors & Theme
# ============================================================================

LASTAGENT_THEME = Theme({
    # Primary brand colors
    "brand.primary": "bold cyan",
    "brand.secondary": "bold magenta",
    "brand.accent": "bold yellow",
    
    # Status colors
    "status.success": "bold green",
    "status.warning": "bold yellow",
    "status.error": "bold red",
    "status.info": "bold blue",
    
    # Agent colors
    "agent.claude": "bold #E07B53",      # Anthropic orange
    "agent.gemini": "bold #4285F4",      # Google blue
    "agent.gpt": "bold #00A67E",         # OpenAI green
    "agent.grok": "bold #1DA1F2",        # X/Twitter blue
    "agent.aider": "bold #9B59B6",       # Purple
    "agent.codex": "bold #00A67E",       # OpenAI green
    "agent.goose": "bold #F39C12",       # Orange
    
    # UI elements
    "ui.header": "bold white on blue",
    "ui.border": "cyan",
    "ui.dim": "dim white",
    "ui.highlight": "bold white",
})

# Global console instance with theme
console = Console(theme=LASTAGENT_THEME)

# ============================================================================
# Logo & Branding
# ============================================================================

LOGO = """
╦  ┌─┐┌─┐┌┬┐╔═╗┌─┐┌─┐┌┐┌┌┬┐
║  ├─┤└─┐ │ ╠═╣│ ┬├┤ │││ │ 
╩═╝┴ ┴└─┘ ┴ ╩ ╩└─┘└─┘┘└┘ ┴ 
"""

TAGLINE = "One Agent to Rule Them All"

# ============================================================================
# Header & Panel Helpers
# ============================================================================

def print_header(title: str, subtitle: Optional[str] = None):
    """Print a branded header panel."""
    content = Text()
    content.append(title, style="bold white")
    if subtitle:
        content.append(f"\n{subtitle}", style="dim white")
    
    panel = Panel(
        content,
        title="[bold cyan]🤖 LastAgent[/]",
        border_style="cyan",
        padding=(0, 2),
    )
    console.print(panel)


def print_logo():
    """Print the LastAgent logo."""
    console.print(Text(LOGO, style="bold cyan"))
    console.print(Text(f"  {TAGLINE}", style="dim white"))
    console.print()


# ============================================================================
# Status Message Helpers
# ============================================================================

def print_success(message: str):
    """Print a success message with checkmark."""
    console.print(f"[status.success]✓[/] {message}")


def print_warning(message: str):
    """Print a warning message with warning icon."""
    console.print(f"[status.warning]⚠[/] {message}")


def print_error(message: str):
    """Print an error message with X icon."""
    console.print(f"[status.error]✗[/] {message}")


def print_info(message: str):
    """Print an info message with info icon."""
    console.print(f"[status.info]ℹ[/] {message}")


# ============================================================================
# Agent-Specific Output
# ============================================================================

def get_agent_style(agent_name: str) -> str:
    """Get the style for a specific agent."""
    agent_lower = agent_name.lower()
    return f"agent.{agent_lower}" if agent_lower in [
        "claude", "gemini", "gpt", "grok", "aider", "codex", "goose"
    ] else "brand.primary"


def print_agent_result(
    agent: str,
    response: str,
    duration_ms: int,
    success: bool,
    confidence: Optional[float] = None,
    render_markdown: bool = True,
):
    """Print a complete agent response with metadata."""
    # Header with agent info
    agent_style = get_agent_style(agent)
    
    header_parts = [
        f"[{agent_style}]📋 Agent: {agent}[/]",
        f"[dim]⏱️ {duration_ms}ms[/]",
    ]
    if confidence:
        header_parts.append(f"[dim]🎯 {confidence:.0%}[/]")
    
    status_icon = "[status.success]✓[/]" if success else "[status.error]✗[/]"
    header_parts.append(f"{status_icon}")
    
    console.print(" │ ".join(header_parts))
    console.print()
    
    # Response content
    if render_markdown and response:
        console.print(Markdown(response))
    elif response:
        console.print(response)


def print_agents_table(agents: list[dict]):
    """Print a formatted table of available agents."""
    table = Table(
        title="Available Agents",
        border_style="cyan",
        header_style="bold white",
        show_lines=True,
    )
    
    table.add_column("Agent", style="bold")
    table.add_column("Type", style="dim")
    table.add_column("Best For", style="italic")
    table.add_column("Status", justify="center")
    
    for agent in agents:
        name = agent.get("name", "Unknown")
        agent_type = agent.get("type", "unknown")
        best_for = agent.get("strengths", [""])[0] if agent.get("strengths") else ""
        available = agent.get("available", True)
        
        status = "[green]●[/]" if available else "[red]○[/]"
        style = get_agent_style(name)
        
        table.add_row(
            f"[{style}]{name}[/]",
            agent_type,
            best_for[:50] + "..." if len(best_for) > 50 else best_for,
            status,
        )
    
    console.print(table)


# ============================================================================
# Decision/Council Output
# ============================================================================

def print_council_decision(
    selected_agent: str,
    confidence: float,
    votes: Optional[dict] = None,
):
    """Print council voting decision."""
    agent_style = get_agent_style(selected_agent)
    
    console.print()
    console.print(
        Panel(
            f"[{agent_style}]{selected_agent}[/] selected with "
            f"[bold]{confidence:.0%}[/] confidence",
            title="[bold cyan]🗳️ Council Decision[/]",
            border_style="cyan",
        )
    )
    
    if votes:
        console.print("[dim]Votes:[/]", end=" ")
        vote_parts = [f"{agent}: {vote}" for agent, vote in votes.items()]
        console.print("[dim]" + " | ".join(vote_parts) + "[/]")
    
    console.print()
