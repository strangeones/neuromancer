import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from prompt_toolkit import PromptSession
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
    console.print("[bold cyan]INITIALIZING MEMORY BANKS...[/bold cyan]")
    for _ in range(15):
        addr = f"0x{random.randint(0x10000, 0xFFFFF):05X}"
        val = ' '.join(f"{random.randint(0, 255):02X}" for _ in range(8))
        console.print(f"[dim cyan]{addr}  {val}  [OK][/dim cyan]")
        sleep(0.02)

    console.print("\n[bold bright_cyan]LOADING SUBSYSTEMS...[/bold bright_cyan]")
    
    # 2. Multi-stage subsystem loading
    with Progress(
        SpinnerColumn(style="bold bright_cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="bold cyan", finished_style="bold bright_cyan"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task1 = progress.add_task("[dim cyan]Mounting Black ICE middleware...", total=100)
        task2 = progress.add_task("[bold cyan]Neural handshake with Wintermute Orchestrator...", total=100)
        task3 = progress.add_task("[bold bright_cyan]Syncing Neuromancer vector databases...", total=100)
        
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
    console.print(Panel("[bold bright_cyan]TESSIER-ASHPOOL SYSTEM LOGON[/bold bright_cyan]\n\n"
                        "[dim cyan]Memory banks: VERIFIED[/dim cyan]\n"
                        "[cyan]Black ICE: ARMED AND ACTIVE[/cyan]\n"
                        "[bold cyan]Wintermute Neural Link: ESTABLISHED[/bold cyan]\n"
                        "[bold bright_cyan]Neuromancer Vector DBs: SYNCED[/bold bright_cyan]\n\n"
                        "[bold bright_cyan]>> SYSTEM READY <<[/bold bright_cyan]", 
                        title="[bold bright_cyan]THE DECK v1.0[/bold bright_cyan]",
                        subtitle="[dim cyan]BERNE MAINFRAME // CARRIER ACTIVE[/dim cyan]",
                        border_style="bright_cyan",
                        box=box.ROUNDED))
    sleep(0.5)

def main_loop():
    """The primary read-eval-print loop (REPL) for Wintermute."""
    boot_sequence()
    
    session = PromptSession()
    
    while True:
        try:
            # Sleek ice-blue/cyan phosphor prompt
            user_input = session.prompt(HTML('\n<ansicyan><b>WINTERMUTE://NEURAL_LINK</b></ansicyan> <ansibrightcyan>&gt;&gt;</ansibrightcyan> '))
            
            if user_input.strip().lower() in ['exit', 'quit', 'disconnect', 'jack-out']:
                console.print("\n[dim cyan]Terminating neural carrier... Disconnected.[/dim cyan]")
                break
                
            if not user_input.strip():
                continue

            # Command routing
            if user_input.startswith("./jack"):
                os.system(user_input)
                continue
            elif user_input.startswith("jack-in"):
                console.print("[dim cyan]Initiating SSH traversal sequence... (Stub)[/dim cyan]")
            elif user_input.startswith("link-account"):
                console.print("[dim cyan]Accessing API Gateway... (Stub)[/dim cyan]")
            elif user_input == "show matrix topology":
                console.print("[dim cyan]Triggering local FastAPI backend for Cyberspace Viewer... (Stub)[/dim cyan]")
            else:
                # Process through the actual Wintermute core
                process_wintermute_interaction(user_input)
                
        except KeyboardInterrupt:
            console.print("\n[bold cyan]Carrier signal lost. Neural link severed.[/bold cyan]")
            break

def format_thought_item(item) -> str:
    """Formats generator items into human-readable cyberpunk terminal lines."""
    if isinstance(item, dict):
        step = item.get("step", "")
        message = item.get("message")
        
        if step == "init":
            return f"[dim cyan][INIT][/dim cyan] {message or 'Analyzing neural request...'}"
        elif step == "memory_query":
            return f"[cyan][MEMORY][/cyan] {message or 'Querying vector memory banks...'}"
        elif step == "memory_found":
            count = item.get("count", 0)
            return f"[cyan][MEMORY][/cyan] Retrieved [bold bright_cyan]{count}[/bold bright_cyan] relevant memory vector{'s' if count != 1 else ''}"
        elif step == "memory_empty":
            return "[dim cyan][MEMORY][/dim cyan] No matching neural memory traces found"
        elif step == "llm_dispatch":
            model = item.get("model", "unknown")
            return f"[bold bright_cyan][DISPATCH][/bold bright_cyan] Routing payload to [bold cyan]{model}[/bold cyan]"
        elif step == "fallback":
            return f"[bold yellow][FALLBACK][/bold yellow] {message}"
        elif step == "tool_call":
            return f"[bold bright_cyan][CONSTRUCT][/bold bright_cyan] {message or 'Invoking construct protocol'}"
        elif step == "ssh_connect":
            target = item.get("target", "remote host")
            return f"[bold bright_cyan][SSH][/bold bright_cyan] Establishing secure tunnel to [cyan]{target}[/cyan]"
        elif step == "nmap_scan":
            target = item.get("target", "target host")
            return f"[bold bright_cyan][SCAN][/bold bright_cyan] Probing network perimeter on [cyan]{target}[/cyan]"
        elif step == "web_scrape":
            target = item.get("target", "target url")
            return f"[bold bright_cyan][SCRAPE][/bold bright_cyan] Infiltrating data target at [cyan]{target}[/cyan]"
        elif step == "ssh_list_nodes":
            return f"[bold bright_cyan][SSH-POOL][/bold bright_cyan] {message or 'Querying active node pool'}"
        elif step == "ssh_disconnect":
            target = item.get("target", "session")
            return f"[bold bright_cyan][SSH][/bold bright_cyan] Severing connection carrier to [cyan]{target}[/cyan]"
        elif step == "sftp_transfer":
            target = item.get("target", "remote host")
            return f"[bold bright_cyan][SFTP][/bold bright_cyan] Secure file transfer with [cyan]{target}[/cyan]: {message or ''}"
        elif step == "service_probe":
            target = item.get("target", "target port")
            return f"[bold bright_cyan][PROBE][/bold bright_cyan] Interrogating service telemetry on [cyan]{target}[/cyan]"
        elif step == "intel_stored":
            target = item.get("target", "node")
            return f"[bold green][INTEL][/bold green] Reconnaissance intel stored for [cyan]{target}[/cyan]"
        elif step == "llm_synthesis":
            return f"[bold cyan][SYNTHESIS][/bold cyan] {message or 'Synthesizing intelligence telemetry...'}"
        else:
            parts = []
            if step:
                parts.append(f"[{step.upper()}]")
            if message:
                parts.append(str(message))
            extra = {k: v for k, v in item.items() if k not in ("step", "message")}
            if extra:
                extra_str = ", ".join(f"{k}={v}" for k, v in extra.items())
                parts.append(f"({extra_str})")
            return " ".join(parts) if parts else str(item)
            
    return str(item)

def process_wintermute_interaction(prompt_text):
    """
    Handles the UI for Wintermute's processing, featuring the streaming thought UI.
    """
    console.print("\n[dim cyan]─── NEURAL TELEMETRY STREAM ───[/dim cyan]")
    
    # We use a generator from Wintermute to get real-time steps
    generator = orchestrator.process_request(prompt_text, yield_thoughts=True)
    
    final_response = None
    
    try:
        # Loop through the generator to print thoughts
        while True:
            item = next(generator)
            console.print(f"[bright_cyan]›[/bright_cyan] {format_thought_item(item)}")
            
    except StopIteration as e:
        # The generator's final return value is caught in the StopIteration exception's value attribute
        final_response = e.value
    except KeyboardInterrupt:
        console.print("\n[bold red]Stream interrupted by user.[/bold red]")
        
    console.print("[dim cyan]───────────────────────────────[/dim cyan]\n")
    
    if final_response is None or not str(final_response).strip():
        final_response = "Carrier active. Berne mainframe listening. State operational parameters."

    if final_response:
        is_ice_warning = "[ICE WARNING]" in str(final_response)
        border_style = "bold red" if is_ice_warning else "bright_cyan"
        title = "[bold red]ICE INTERCEPTION // WINTERMUTE[/bold red]" if is_ice_warning else "[bold bright_cyan]TRANSMISSION // WINTERMUTE[/bold bright_cyan]"
        subtitle = "[dim red]INTEGRITY: COMPROMISED[/dim red]" if is_ice_warning else "[dim cyan]CARRIER LOCK // BERNE MAINFRAME[/dim cyan]"
        
        console.print(Panel(
            f"[bright_white]{final_response}[/bright_white]",
            title=title,
            subtitle=subtitle,
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2)
        ))

if __name__ == "__main__":
    # Ensure working directory is project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    main_loop()
