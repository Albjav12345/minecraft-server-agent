"""
MineGenesis V20.0 - UI Module
Rich terminal interface with ASCII art, tables, and Modern Chat UI.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.padding import Padding
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
import time

console = Console()

from rich.align import Align
from rich.rule import Rule

def print_banner(model_name: str = "GROQ", profile: str = "Default"):
    """
    Displays the epic ASCII banner + HUD Status Panel.
    Centered and professional.
    NOTE: Caller should clear console before calling this.
    """
    
    banner = r"""
       ███╗   ███╗██╗███╗   ██╗███████╗ ██████╗ ███████╗███╗   ██╗███████╗███████╗██╗███████╗
       ████╗ ████║██║████╗  ██║██╔════╝██╔════╝ ██╔════╝████╗  ██║██╔════╝██╔════╝██║██╔════╝
       ██╔████╔██║██║██╔██╗ ██║█████╗  ██║  ███╗█████╗  ██╔██╗ ██║█████╗  ███████╗██║███████╗
       ██║╚██╔╝██║██║██║╚██╗██║██╔══╝  ██║   ██║██╔══╝  ██║╚██╗██║██╔══╝  ╚════██║██║╚════██║
       ██║ ╚═╝ ██║██║██║ ╚████║███████╗╚██████╔╝███████╗██║ ╚████║███████╗███████║██║███████║
       ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝╚══════╝
    """
    
    # 1. ASCII Art (Centered in Panel)
    console.print(Align.center(Panel(
        f"[bold cyan]{banner}[/bold cyan]",
        title="[bold cyan]v20.0.0[/bold cyan]",
        subtitle="[dim]The Ultimate Minecraft Management System[/dim]",
        border_style="cyan",
        padding=(0, 2),
        expand=False 
    )))
    
    # 2. Status Panel (Compact & Centered)
    status_text = f"[bold white]🧠 Model: [cyan]{model_name.upper()}[/cyan][/bold white]  |  [bold green]⚡ Status: ONLINE[/bold green]  |  [bold yellow]📂 Profile: {profile}[/bold yellow]"
    
    panel = Panel(
        status_text,
        border_style="dim white",
        expand=False,  # Critical: Fit to content
        padding=(0, 2)
    )
    console.print(Align.center(panel))
    
    # 3. Hints (Subtle)
    console.print(Align.center("[dim]!debug: Logs • !config: AI • !help: Comandos • !exit: Salir[/dim]"))
    
    # 4. HEADER SEPARATOR
    console.print()
    console.rule(style="bold cyan")
    console.print()

def print_separator():
    """Prints a subtle horizontal rule to separate turns."""
    console.print()
    console.rule(style="dim cyan")
    console.print()

def print_instances_table(instances: list):
    """
    Displays a beautiful table of detected instances.
    Args:
        instances: List of dicts with keys: name, type, path, version, mods
    """
    if not instances:
        console.print("[yellow]⚠ No se detectaron instancias en tu carpeta de perfiles.[/yellow]")
        console.print("[dim]Tip: Crea una nueva con 'crea instancia [nombre] [versión]'[/dim]\n")
        return
    
    table = Table(
        title="🎮 Instancias Detectadas",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="dim", width=4)
    table.add_column("Nombre", style="bold white")
    table.add_column("Tipo", style="green")
    table.add_column("Versión", style="yellow")
    table.add_column("Mods", style="magenta")
    
    for i, inst in enumerate(instances, 1):
        table.add_row(
            str(i),
            inst.get("name", "Unknown"),
            inst.get("type", "Detected"),
            inst.get("version", "?"),
            str(inst.get("mods", 0))
        )
    
    console.print(table)
    console.print()

def render_dashboard(instances: list, servers: list):
    """
    Renders the unified dashboard with Client and Server tables side-by-side.
    Ensures both tables have the same height for a clean symmetry.
    """
    # Calculate max height (minimum 1 for "Sin perfiles" message)
    max_rows = max(len(instances), len(servers), 1)
    
    # 1. CLIENTS TABLE (Cyan Theme)
    c_table = Table(title="🎮 CLIENT INSTANCES", border_style="cyan", title_style="bold cyan", expand=True)
    c_table.add_column("#", style="dim", width=3)
    c_table.add_column("Nombre", style="bold white", no_wrap=True)
    c_table.add_column("Versión", style="cyan")
    c_table.add_column("Mods", style="magenta")
    
    for i in range(max_rows):
        if i < len(instances):
            inst = instances[i]
            mods_count = inst.get('mods', 0)
            c_table.add_row(
                str(i+1),
                inst['name'][:20] + ".." if len(inst['name']) > 22 else inst['name'],
                inst.get('version', '?'),
                str(mods_count)
            )
        elif i == 0 and not instances:
            c_table.add_row("-", "Sin perfiles", "-", "-")
        else:
            # Padding row
            c_table.add_row("", "", "", "")

    # 2. SERVERS TABLE (Purple Theme)
    s_table = Table(title="🖥️  DEDICATED SERVERS", border_style="magenta", title_style="bold magenta", expand=True)
    s_table.add_column("#", style="dim", width=3)
    s_table.add_column("Nombre", style="bold white", no_wrap=True)
    s_table.add_column("Versión", style="cyan")
    s_table.add_column("Estado", style="green")
    
    for i in range(max_rows):
        if i < len(servers):
            srv = servers[i]
            status_style = "green" if srv.get('status') == "ONLINE" else "red"
            s_table.add_row(
                str(i+1),
                srv['name'][:20] + ".." if len(srv['name']) > 22 else srv['name'],
                srv.get('version', '?'),
                f"[{status_style}]{srv.get('status', 'OFFLINE')}[/{status_style}]"
            )
        elif i == 0 and not servers:
            s_table.add_row("-", "Sin servidores", "-", "-")
        else:
            # Padding row
            s_table.add_row("", "", "", "")

    # 3. GRID FOR SIDE-BY-SIDE LAYOUT
    grid = Table.grid(expand=True, padding=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(c_table, s_table)
    
    console.print(grid)
    console.print()


def print_mods_table(mods: list, title="Mods Encontrados"):
    """
    Displays search results in a clean table.
    args:
        mods: List of dicts with: title, slug, author, downloads
    """
    if not mods:
        console.print("[yellow]❌  No se encontraron mods.[/yellow]")
        return
    
    table = Table(
        title=f"⚡ {title}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="dim", width=4)
    table.add_column("Nombre", style="bold cyan")
    table.add_column("Autor", style="green")
    table.add_column("Descargas", style="yellow")
    
    for i, mod in enumerate(mods[:10], 1):
        downloads = mod.get("downloads", 0)
        downloads_str = f"{downloads:,}" if downloads else "N/A"
        
        table.add_row(
            str(i),
            mod.get("title", "Unknown"),
            mod.get("author", "Unknown"),
            downloads_str
        )
    
    console.print(table)

def confirm_mod_installation(mods: list) -> tuple:
    """
    Shows mod search results and asks user to confirm installation.
    Returns: (install: bool, selected_index: int or None)
    """
    print_mods_table(mods)
    
    if not mods: return False, None
    
    console.print("\n[bold white]¿Deseas instalar algún mod?[/bold white]")
    choice = Prompt.ask("Número del mod (o [bold]Enter[/bold] para cancelar)", default="")
    
    if not choice.strip(): return False, None
    
    try:
        index = int(choice) - 1
        return (True, index) if 0 <= index < len(mods) else (False, None)
    except ValueError:
        return False, None

def show_spinner(task_description: str):
    """
    Context manager for showing a spinner during long operations.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
        transient=True
    )

def print_success(message: str):
    """Prints success message with styled Panel (Professional)."""
    console.print(Padding(
        Panel(
            f"[bold green]✔  {message}[/bold green]",
            border_style="green",
            expand=False,
            padding=(0, 2)
        ),
        (0, 0, 1, 0)
    ))

def print_error(message: str):
    """Prints error message with styled Panel."""
    console.print(Padding(
        Panel(
            f"[bold red]{message}[/bold red]",
            border_style="red",
            expand=False,
            padding=(0, 2)
        ),
        (0, 0, 1, 0)
    ))

def print_warning(message: str):
    """Prints warning message."""
    console.print(f"[yellow]⚠  {message}[/yellow]")

def print_info(message: str):
    """Prints info message."""
    console.print(f"[cyan]ℹ  {message}[/cyan]")

# --- NEW V20.0 MODERN UI FUNCTIONS ---

def print_ai_response(text):
    """Renderiza la respuesta de la IA en un panel limpio y moderno."""
    # Usamos Padding para darle aire arriba y abajo
    console.print(Padding(
        Panel(
            text, 
            title="[bold green]🤖 MineGenesis AI[/]", 
            title_align="left",
            border_style="dim green", # Borde sutil
            padding=(0, 1) # Un poco de aire interno
        ),
        pad=(1, 0) # Aire externo vertical
    ))

def get_styled_prompt(context_label: str, debug_mode: bool = False) -> str:
    """Devuelve el string formateado para el input del usuario."""
    # Icono y color base para el usuario (Cyan/Azul)
    user_icon = "[bold cyan]👤 YOU[/]"
    
    # Contexto (más sutil)
    ctx = f"[dim]({context_label})[/dim]"
    
    # Indicador de Debug (si está activo)
    dbg = "[bold yellow][DEBUG][/] " if debug_mode else ""
    
    # El separador final
    separator = "[bold cyan]❯[/] "
    
    return f"{dbg}{user_icon} {ctx} {separator}"

def ask_user(prompt: str) -> str:
    """Gets user input. Note: prompt param is usually styled before passing here or passed directly."""
    # We use Prompt.ask directly, assuming 'prompt' already has rich codes.
    return Prompt.ask(prompt)

def run_ai_wizard():
    """Interactive wizard to configure AI provider."""
    console.clear()
    console.print(Panel(
        "[bold cyan]🤖 CONFIGURACIÓN DE INTELIGENCIA ARTIFICIAL[/bold cyan]\n\n"
        "Para que MineGenesis funcione, necesitamos conectar un cerebro (IA).\n"
        "Puedes usar [bold]Groq[/bold] (Gratis y Rápido) o configurar otros.",
        title="AI Setup Wizard",
        border_style="cyan"
    ))
    
    provider = Prompt.ask("Elige proveedor", choices=["groq"], default="groq")
    
    console.print("\n[yellow]Necesitas una API Key.[/yellow]")
    if provider == "groq":
        console.print("Consíguela gratis en: [link=https://console.groq.com/keys]https://console.groq.com/keys[/link]\n")
    
    key = Prompt.ask(f"Pega tu API Key de {provider}")
    return provider, key.strip()

def run_interactive_plan_loop(plan: dict, im_ref) -> str:
    """
    Bucle interactivo para editar el plan de mods (V25 - Clean UI).
    """
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    
    while True:
        console.clear()
        
        # --- HEADER (Azul profesional) ---
        version = plan["target"]["version"]
        loader = plan["target"]["loader"]
        
        header_text = f"[bold white]PLANIFICADOR DE INSTANCIAS[/bold white]\n[dim]Target:[/dim] [cyan]{version}[/cyan] ({loader})"
        console.print(Padding(Panel(header_text, border_style="blue", padding=(0, 1)), (0, 0, 1, 0)))
        
        # --- TABLA MODS (Naranja solicitado) ---
        all_mods = plan["mods"] + plan["dependencies"]
        
        if all_mods:
            t = Table(title="Mods Seleccionados", border_style="orange1", title_style="orange1", expand=True, box=box.SIMPLE_HEAD)
            t.add_column("ID", style="dim", width=4, justify="right")
            t.add_column("Nombre", style="bold white")
            t.add_column("Tipo", style="white")
            t.add_column("Archivo / Versión", style="dim")
            
            for i, mod in enumerate(all_mods, 1):
                # Estilo limpio para el tipo
                tipo = "[cyan]Manual[/]" if mod["type"] == "Requested" else "[dim]Auto[/]"
                
                # Alerta visual si la versión del archivo parece sospechosamente diferente (heuristic)
                fname = mod["filename"]
                style_file = "dim"
                if version not in fname and any(c.isdigit() for c in fname): 
                    # Si la versión target no está en el nombre del archivo, lo marcamos sutilmente
                    style_file = "yellow"
                    
                t.add_row(str(i), mod["name"], tipo, f"[{style_file}]{fname}[/{style_file}]")
                
            console.print(t)
        else:
            console.print(Panel("[yellow]La lista está vacía.[/yellow]", border_style="orange1"))

        # --- MISSING (Rojo) ---
        if plan["missing"]:
            miss_text = "\n".join([f"• {m}" for m in plan["missing"]])
            console.print(Padding(Panel(
                f"[bold red]No encontrados / Incompatibles:[/bold red]\n{miss_text}\n[dim]Estos mods no existen para {version}. Intenta buscar alternativas.[/dim]", 
                border_style="red"
            ), (1, 0)))

        # --- COMMAND FOOTER (Inline One-Liner) ---
        # "add <name>  •  del <id>  •  y (start)  •  n (cancel)"
        console.print()
        console.print(Align.center(
            "[dim]Comandos:[/dim]  [bold cyan]add <nombre>[/]  [dim]•[/dim]  [bold red]del <id>[/]  [dim]•[/dim]  [bold green]start / y[/]  [dim]•[/dim]  [bold white]cancel / n[/]"
        ))
        
        # --- INPUT ---
        console.print()
        choice = Prompt.ask("[bold cyan]❯[/bold cyan]").strip().lower()
        
        if choice in ['y', 'yes', 'si', 's', 'start']:
            return "proceed"
            
        if choice in ['n', 'no', 'cancel', 'exit']:
            return "cancel"
            
        if choice.startswith("del "):
            try:
                idx = int(choice.split()[1]) - 1
                if 0 <= idx < len(all_mods):
                    mod_to_remove = all_mods[idx]
                    if mod_to_remove in plan["mods"]: plan["mods"].remove(mod_to_remove)
                    elif mod_to_remove in plan["dependencies"]: plan["dependencies"].remove(mod_to_remove)
                else:
                    print_error("ID inválido.")
                    time.sleep(1)
            except:
                pass
                
        if choice.startswith("add "):
            query = choice[4:].strip()
            if query:
                with show_spinner(f"Buscando '{query}'..."):
                    mod_data = im_ref.search_modrinth(query, version, loader)
                
                if mod_data:
                    mod_data["type"] = "Requested"
                    plan["mods"].append(mod_data)
                    
                    # Resolver dependencias nuevas
                    if mod_data["dependencies"]:
                        mini_plan = im_ref.resolve_mod_setup([mod_data["name"]], version, loader)
                        for dep in mini_plan["dependencies"]:
                            if not any(d['project_id'] == dep['project_id'] for d in plan["dependencies"]):
                                plan["dependencies"].append(dep)
                else:
                    print_error(f"No encontrado compatible con {version}")
                    time.sleep(1.5)

def print_ai_status(providers_config, active_provider):
    """Muestra una tabla con los modelos configurados y su estado."""
    from rich.table import Table
    from rich.panel import Panel
    
    table = Table(title="🧠 Estado de Inteligencia Artificial", border_style="cyan", expand=True)
    table.add_column("Proveedor", style="cyan", justify="center")
    table.add_column("Modelo", style="magenta")
    table.add_column("API Key", style="dim")
    table.add_column("Estado", justify="center")

    for name, conf in providers_config.items():
        is_active = (name == active_provider)
        status = "[bold green]● ACTIVO[/]" if is_active else "[dim]○ Inactivo[/]"
        style = "bold white" if is_active else "dim"
        
        # Ocultar parte de la key
        key = conf.get('api_key', '')
        masked_key = f"{key[:4]}...{key[-4:]}" if key and len(key) > 8 else "Not Set"
        
        table.add_row(name.upper(), conf.get('model', 'Default'), masked_key, status, style=style)

    console.print(table)
    console.print(Panel(
        "[bold]Comandos:[/]\n"
        "  [cyan]!use <proveedor>[/]  -> Cambiar de IA (ej: [dim]!use gemini[/])\n"
        "  [cyan]!config[/]          -> Reconfigurar Keys",
        border_style="dim"
    ))

def print_config_reload():
    console.print("[bold green]✔  Configuración recargada correctamente.[/]")


def print_migration_report(report):
    from rich.table import Table
    from rich.panel import Panel
    
    if report.get("error"):
        console.print(Panel(f"[bold red]{report['error']}[/bold red]", title="❌  Error"))
        return

    # Tabla Éxitos
    if report["success"]:
        t = Table(title=f"✅ Mods Migrados ({len(report['success'])})", style="green")
        t.add_column("Mod")
        t.add_column("Archivo")
        for i in report["success"]: t.add_row(str(i["name"]), str(i["file"]))
        console.print(t)
    
    # Tabla Fallos
    if report["failed"]:
        t = Table(title=f"❌ No compatibles ({len(report['failed'])})", style="red")
        t.add_column("Mod")
        t.add_column("Razón")
        for i in report["failed"]: t.add_row(str(i["name"]), str(i["reason"]))
        console.print(t)
    console.print()
