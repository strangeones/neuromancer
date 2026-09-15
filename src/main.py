import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from time import sleep

from src.wintermute import orchestrator

# Initialize the Deck Console
console = Console()

def boot_sequence():
    """Simulates the terminal boot sequence for The Deck."""
    console.clear()
    console.print(Panel("[bold green]TESSIER-ASHPOOL SYSTEM LOGON[/bold green]\n"
                        "[dim]Establishing connection to Wintermute Core...[/dim]\n"
                        "[dim]Neuromancer vector databases synced...[/dim]\n"
                        "[bold cyan]ICE Protocols: ACTIVE[/bold cyan]", 
                        title="THE DECK v1.0", border_style="green"))
    sleep(0.5)

def main_loop():
    """The primary read-eval-print loop (REPL) for Wintermute."""
    boot_sequence()
    
    while True:
        try:
            # Cyberpunk prompt styling
            user_input = Prompt.ask("\n[bold cyan]WINTERMUTE[/bold cyan]@[bold green]MATRIX[/bold green] >")
            
            if user_input.strip().lower() in ['exit', 'quit', 'disconnect', 'jack-out']:
                console.print("\n[bold red]Disconnecting from the Matrix... Goodbye.[/bold red]")
                break
                
            if not user_input.strip():
                continue

            # Command routing
            if user_input.startswith("jack-in"):
                console.print("[dim]Initiating SSH traversal sequence... (Stub)[/dim]")
            elif user_input.startswith("link-account"):
                console.print("[dim]Accessing API Gateway... (Stub)[/dim]")
            elif user_input == "show matrix topology":
                console.print("[dim]Triggering local FastAPI backend for Cyberspace Viewer... (Stub)[/dim]")
            else:
                # Process through the actual Wintermute core
                process_wintermute_interaction(user_input)
                
        except KeyboardInterrupt:
            console.print("\n[bold red]Connection severed. Disconnecting...[/bold red]")
            break

def process_wintermute_interaction(prompt_text):
    """
    Handles the UI for Wintermute's processing, featuring the streaming thought UI.
    """
    console.print("\n[dim green]--- THOUGHT STREAM ---[/dim green]")
    
    # We use a generator from Wintermute to get real-time steps
    generator = orchestrator.process_request(prompt_text, yield_thoughts=True)
    
    final_response = None
    
    try:
        # Loop through the generator to print thoughts
        while True:
            item = next(generator)
            console.print(f"[green]> {item}[/green]")
            sleep(0.3) # Artificial delay for aesthetic effect
            
    except StopIteration as e:
        # The generator's final return value is caught in the StopIteration exception's value attribute
        final_response = e.value
        
    console.print("[dim green]------------------------[/dim green]\n")
    
    if final_response:
        console.print(Panel(
            f"[bold white]{final_response}[/bold white]",
            title="Wintermute Response",
            border_style="cyan"
        ))

if __name__ == "__main__":
    # Ensure working directory is project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    main_loop()
