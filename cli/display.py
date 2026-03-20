"""Terminal display formatting for the leox CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_banner(message: str):
    """Print a styled banner."""
    console.print(Panel(f"[bold cyan]{message}[/]", border_style="cyan"))


def print_ok(message: str):
    """Print a success message."""
    console.print(f"  [green]✓[/] {message}")


def print_error(message: str):
    """Print an error message."""
    console.print(f"  [red]✗[/] {message}")


def print_status(
    compose_output: str | None,
    wa_status: dict | None,
    brain_status: dict | None,
):
    """Print a formatted status overview."""
    console.print()
    console.print(Panel("[bold cyan]● leox[/]", border_style="cyan"))

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Service", style="bold")
    table.add_column("Status")
    table.add_column("Detail")

    # WhatsApp service
    if wa_status:
        ws = wa_status.get("status", "unknown")
        number = wa_status.get("number", "?")
        uptime = wa_status.get("uptime", 0)
        status_icon = "[green]✓[/]" if ws == "connected" else "[yellow]○[/]"
        detail = f"@+{number}" if ws == "connected" else ws
        table.add_row(f"  ├── whatsapp-service", status_icon, detail)
    else:
        table.add_row("  ├── whatsapp-service", "[red]✗[/]", "no responde")

    # Brain service
    if brain_status and brain_status.get("status") == "ok":
        table.add_row("  ├── brain (FastAPI)", "[green]✓[/]", "puerto 8000")
    else:
        table.add_row("  ├── brain (FastAPI)", "[red]✗[/]", "no responde")

    # ChromaDB (Phase 2+)
    table.add_row("  └── chromadb", "[dim]○[/]", "[dim]pendiente (fase 2)[/]")

    console.print(table)
    console.print()
