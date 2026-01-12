"""
LastAgent Spinners Module

Animated spinners and progress indicators for long-running operations.
"""

from contextlib import contextmanager
from typing import Optional, Generator
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


class AgentSpinner:
    """
    Context manager for animated spinners during agent operations.
    
    Usage:
        with AgentSpinner("Council voting...") as spinner:
            result = await vote()
            spinner.update("Executing with Claude...")
            response = await execute()
    """
    
    SPINNER_STYLES = {
        "default": "dots",
        "council": "dots12",
        "execution": "bouncingBar",
        "thinking": "arc",
    }
    
    def __init__(
        self,
        message: str,
        console: Optional[Console] = None,
        spinner_type: str = "default",
        show_time: bool = True,
    ):
        self.message = message
        self.console = console or Console()
        self.spinner_name = self.SPINNER_STYLES.get(spinner_type, "dots")
        self.show_time = show_time
        self._live: Optional[Live] = None
        self._current_text = message
    
    def _render(self) -> Panel:
        """Render the spinner panel."""
        spinner = Spinner(self.spinner_name, text=self._current_text, style="cyan")
        return Panel(
            spinner,
            border_style="dim cyan",
            padding=(0, 1),
        )
    
    def update(self, message: str):
        """Update the spinner message."""
        self._current_text = message
        if self._live:
            self._live.update(self._render())
    
    def __enter__(self) -> "AgentSpinner":
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=10,
            transient=True,
        )
        self._live.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._live:
            self._live.__exit__(exc_type, exc_val, exc_tb)
        return False


@contextmanager
def spinner(
    message: str,
    console: Optional[Console] = None,
    spinner_type: str = "default",
) -> Generator[AgentSpinner, None, None]:
    """
    Context manager for quick spinner usage.
    
    Usage:
        with spinner("Processing...") as s:
            do_work()
            s.update("Almost done...")
    """
    agent_spinner = AgentSpinner(
        message=message,
        console=console,
        spinner_type=spinner_type,
    )
    with agent_spinner:
        yield agent_spinner


# ============================================================================
# Phase-Specific Spinners
# ============================================================================

@contextmanager
def council_spinner(console: Optional[Console] = None) -> Generator[AgentSpinner, None, None]:
    """Spinner for council voting phase."""
    with spinner("🗳️ Council voting...", console, "council") as s:
        yield s


@contextmanager
def execution_spinner(
    agent: str,
    console: Optional[Console] = None,
) -> Generator[AgentSpinner, None, None]:
    """Spinner for agent execution phase."""
    with spinner(f"⚡ Executing with {agent}...", console, "execution") as s:
        yield s


@contextmanager
def thinking_spinner(console: Optional[Console] = None) -> Generator[AgentSpinner, None, None]:
    """Spinner for thinking/processing phase."""
    with spinner("🤔 Thinking...", console, "thinking") as s:
        yield s
