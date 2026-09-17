import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.formatted_text import HTML
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from time import sleep
import random

from src.wintermute import orchestrator

# Initialize the Deck Console
console = Console()

def boot_sequence():
    """Simulates the terminal boot sequence for The Deck."""
    console.clear()
    
    # 1. Fast hex memory checks
    console.print("[bold green]INITIALIZING MEMORY BANKS...[/bold green]")
    for _ in range(15):
        addr = f"0x{random.randint(0x10000, 0xFFFFF):05X}"
        val = ' '.join(f"{random.randint(0, 255):02X}" for _ in range(8))
        console.print(f"[dim green]{addr}  {val}  [OK][/dim green]")
        sleep(0.02)

    console.print("\n[bold cyan]LOADING SUBSYSTEMS...[/bold cyan]")
    
    # 2. Multi-stage subsystem loading
    with Progress(
        SpinnerColumn(style="bold cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="bold green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task1 = progress.add_task("[bold red]Mounting Black ICE middleware...", total=100)
        task2 = progress.add_task("[bold cyan]Neural handshake with Wintermute Orchestrator...", total=100)
        task3 = progress.add_task("[bold magenta]Syncing Neuromancer vector databases...", total=100)
        
        while not progress.finished:
            progress.update(task1, advance=random.uniform(10, 20))
            if progress.tasks[0].completed > 30:
                progress.update(task2, advance=random.uniform(8, 15))
            if progress.tasks[1].completed > 20:
                progress.update(task3, advance=random.uniform(10, 18))
            sleep(0.05)

    # 3. Final Logon Panel
    sleep(0.2)
    console.clear()
    console.print(Panel("[bold green]TESSIER-ASHPOOL SYSTEM LOGON[/bold green]\n\n"
                        "[dim]Memory banks: VERIFIED[/dim]\n"
                        "[bold red]Black ICE: ARMED AND ACTIVE[/bold red]\n"
                        "[bold cyan]Wintermute Neural Link: ESTABLISHED[/bold cyan]\n"
                        "[bold magenta]Neuromancer Vector DBs: SYNCED[/bold magenta]\n\n"
                        "[bold green]>> SYSTEM READY <<[/bold green]", 
                        title="[bold green]THE DECK v1.0[/bold green]", border_style="green"))
    sleep(0.5)

def main_loop():
    """The primary read-eval-print loop (REPL) for Wintermute."""
    boot_sequence()
    
    session = PromptSession()
    
    while True:
        try:
            # Cyberpunk prompt styling
            user_input = session.prompt(HTML('\n<ansicyan><b>WINTERMUTE</b></ansicyan>@<ansigreen><b>MATRIX</b></ansigreen> &gt; '))
            
            if user_input.strip().lower() in ['exit', 'quit', 'disconnect', 'jack-out']:
                console.print("\n[bold red]Jacking out...[/bold red]")
                break
                
            if not user_input.strip():
                continue

            # Command routing
            if user_input.startswith("./jack"):
                run_in_terminal(lambda: os.system(user_input))
                continue
            elif user_input.startswith("jack-in"):
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
            
    except StopIteration as e:
        # The generator's final return value is caught in the StopIteration exception's value attribute
        final_response = e.value
    except KeyboardInterrupt:
        console.print("\n[bold red]Stream interrupted by user.[/bold red]")
        
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
