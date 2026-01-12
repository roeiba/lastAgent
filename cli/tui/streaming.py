"""
LastAgent Streaming Module

Real-time streaming output renderer for agent responses.
Handles token-by-token rendering with proper buffering for code blocks.
"""

import asyncio
from typing import AsyncIterator, Optional, Callable
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from rich.panel import Panel


class StreamingRenderer:
    """
    Renders streaming text responses with markdown support.
    
    Buffers content to properly render code blocks and other
    markdown elements that span multiple tokens.
    
    Usage:
        renderer = StreamingRenderer(console)
        async for chunk in response_stream:
            renderer.update(chunk)
        renderer.finish()
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        render_markdown: bool = True,
        show_cursor: bool = True,
    ):
        self.console = console or Console()
        self.render_markdown = render_markdown
        self.show_cursor = show_cursor
        self._buffer = ""
        self._live: Optional[Live] = None
        self._in_code_block = False
        self._code_fence_count = 0
    
    def _render_content(self, content: str, finished: bool = False) -> Text | Markdown:
        """Render accumulated content."""
        if not content:
            cursor = "▌" if self.show_cursor and not finished else ""
            return Text(cursor, style="bold cyan")
        
        if self.render_markdown:
            # Add cursor to markdown
            display_content = content
            if self.show_cursor and not finished:
                display_content += " ▌"
            return Markdown(display_content)
        else:
            cursor = "▌" if self.show_cursor and not finished else ""
            return Text(content + cursor)
    
    def start(self):
        """Start the live renderer."""
        self._live = Live(
            self._render_content(""),
            console=self.console,
            refresh_per_second=15,
            vertical_overflow="visible",
        )
        self._live.start()
    
    def update(self, chunk: str):
        """Update with new content chunk."""
        self._buffer += chunk
        
        # Track code blocks for proper buffering
        self._code_fence_count += chunk.count("```")
        self._in_code_block = self._code_fence_count % 2 == 1
        
        if self._live:
            self._live.update(self._render_content(self._buffer))
    
    def finish(self):
        """Finish streaming and show final content."""
        if self._live:
            self._live.update(self._render_content(self._buffer, finished=True))
            self._live.stop()
    
    def get_content(self) -> str:
        """Get the accumulated content."""
        return self._buffer
    
    def __enter__(self) -> "StreamingRenderer":
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False


async def stream_response(
    response_iterator: AsyncIterator[str],
    console: Optional[Console] = None,
    render_markdown: bool = True,
    on_chunk: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Stream response chunks to the console with live rendering.
    
    Args:
        response_iterator: Async iterator yielding response chunks
        console: Rich console (uses default if not provided)
        render_markdown: Whether to render as markdown
        on_chunk: Optional callback for each chunk
    
    Returns:
        Complete response text
    """
    renderer = StreamingRenderer(
        console=console,
        render_markdown=render_markdown,
    )
    
    with renderer:
        async for chunk in response_iterator:
            renderer.update(chunk)
            if on_chunk:
                on_chunk(chunk)
    
    return renderer.get_content()


def print_streaming_mock(
    text: str,
    console: Optional[Console] = None,
    delay: float = 0.02,
    render_markdown: bool = True,
):
    """
    Print text with simulated streaming effect.
    Useful for demos and testing.
    
    Args:
        text: Text to display
        console: Rich console
        delay: Delay between characters in seconds
        render_markdown: Whether to render as markdown
    """
    import time
    
    renderer = StreamingRenderer(
        console=console,
        render_markdown=render_markdown,
    )
    
    with renderer:
        for char in text:
            renderer.update(char)
            time.sleep(delay)
