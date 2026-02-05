from agent.data.database import DatabaseManager
import click
from rich.console import Console

console = Console()

@click.group()
def cli():
    """Pickleball Market Intelligence Agent"""
    pass

@cli.command()
def init():
    """Initialize database"""
    console.print("🏓 Initializing Pickleball Agent...", style="bold green")
    db = DatabaseManager()
    db.initialize_db()
    console.print("✅ Database initialized!", style="bold green")

@cli.command() 
def export():
    """Export leads to CSV"""
    console.print("📊 Exporting leads...", style="bold cyan")
    db = DatabaseManager()
    db.export_entities("exports/leads.csv")
    console.print("✅ Export completed: exports/leads.csv", style="bold green")

if __name__ == "__main__":
    cli()
