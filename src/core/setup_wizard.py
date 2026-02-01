"""
MineGenesis V7.0 - Setup Wizard
Handles interactive onboarding, API key acquisition, and environment configuration.
"""
import os
import webbrowser
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

PROVIDERS = {
    "1": {
        "name": "Groq",
        "url": "https://console.groq.com/keys",
        "desc": "Gratis, Extremadamente Rápido (Recomendado)",
        "model": "llama-3.3-70b-versatile",
        "env_var": "GROQ_API_KEY"
    },
    "2": {
        "name": "Google Gemini",
        "url": "https://aistudio.google.com/app/apikey",
        "desc": "Balanceado, Gran Ventana de Contexto",
        "model": "gemini-pro",
        "env_var": "GEMINI_API_KEY"
    },
    "3": {
        "name": "OpenAI",
        "url": "https://platform.openai.com/api-keys",
        "desc": "Potente, Costoso (GPT-4)",
        "model": "gpt-4-turbo",
        "env_var": "OPENAI_API_KEY"
    },
    "4": {
        "name": "Anthropic",
        "url": "https://console.anthropic.com/settings/keys",
        "desc": "Claude 3.5 Sonnet (Excelente para código)",
        "model": "claude-3-5-sonnet-20240620",
        "env_var": "ANTHROPIC_API_KEY"
    }
}

def run_onboarding():
    """Runs the initial setup wizard."""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Import UI to show banner first
    import src.core.ui as ui
    ui.print_banner(model_name="SETUP", profile="Configuración Inicial")
    
    console.print()
    console.print(Panel(
        "[bold cyan]🚀 BIENVENIDO A MINEGENESIS V7.0[/bold cyan]\n\n"
        "Antes de comenzar, necesitamos configurar tu Inteligencia Artificial.\n"
        "Este 'cerebro' te ayudará a gestionar tus servidores y mods.",
        title="Setup Wizard",
        border_style="cyan"
    ))

    # Step 1: Select Provider
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Proveedor", width=15)
    table.add_column("Descripción")
    
    for key, data in PROVIDERS.items():
        table.add_row(key, data["name"], data["desc"])
    
    console.print(table)
    console.print()
    
    choice = Prompt.ask("Selecciona tu proveedor", choices=list(PROVIDERS.keys()), default="1")
    selected_provider = PROVIDERS[choice]
    
    # Step 2: Get Key
    console.print(f"\n[bold green]Has elegido {selected_provider['name']}.[/bold green]")
    console.print("Para continuar, necesitamos tu API Key.")
    
    if Confirm.ask(f"¿Abrir {selected_provider['name']} Console para obtener la key?", default=True):
        console.print(f"Abriendo: {selected_provider['url']}...")
        webbrowser.open(selected_provider['url'])
    
    console.print()
    api_key = Prompt.ask(f"[bold yellow]Pegue su API Key de {selected_provider['name']} aquí[/bold yellow]", password=False)
    
    if not api_key:
        console.print("[red]❌ Error: La API Key no puede estar vacía.[/red]")
        sys.exit(1)

    # TEST CONNECTION
    console.print("\n[dim italic]🔌 Verificando conexión con el proveedor...[/dim italic]", end="\r")
    
    validation_status = "success"
    warning_msg = ""
    
    try:
        from src.ai.llm_client import get_client
        
        # Create client and test
        provider_key = selected_provider["name"].lower()
        test_client = get_client(provider_key, api_key)
        
        # Simple test query
        test_response = test_client.send(
            "You are a helpful assistant.",
            "Respond with only: OK"
        )
        
        # Clear test message
        console.print(" " * 60, end="\r")
        
        if test_response and "ok" in test_response.lower():
            # Success - will be shown in final panel
            pass
        else:
            validation_status = "warning"
            warning_msg = "La respuesta de la IA fue inesperada (posible Key inválida o sin saldo)."
            
    except Exception as e:
        console.print(" " * 60, end="\r")
        console.print(f"[red]❌ Error al conectar: {e}[/red]")
        
        retry = Confirm.ask("¿Deseas reintentar con otra key?", default=True)
        if retry:
            run_onboarding()
            return
        else:
            # User chose to proceed despite error? Or exit? 
            # If they say no to retry, usually we exit. 
            # But maybe they want to save anyway? 
            # The previous code exited. Let's keep exit for error, 
            # but for "warning" (no exception but bad response) we proceed with orange.
            sys.exit(1)

    # Step 3: Save to .env
    save_to_env(selected_provider["env_var"], api_key)
    
    # Save active provider to settings.json
    update_settings_provider(selected_provider["name"].lower(), selected_provider["model"])

    # Final Panel Logic
    if validation_status == "success":
        panel_color = "green"
        panel_title = "Success"
        status_msg = "[green]✅ ¡Configuración Completada![/green]"
        extra_info = ""
    else:
        panel_color = "orange1"
        panel_title = "Completed with Warnings"
        status_msg = "[yellow]⚠️ Configuración Guardada (Con Advertencias)[/yellow]"
        extra_info = f"\n[bold yellow]Advertencia:[/bold yellow] {warning_msg}\nEs posible que la IA no responda correctamente."

    console.print(Panel(
        f"{status_msg}\n\n"
        f"Proveedor: [bold]{selected_provider['name']}[/bold]\n"
        f"Modelo: {selected_provider['model']}\n"
        f"{extra_info}",
        title=panel_title,
        border_style=panel_color
    ))
    
    Prompt.ask("Presiona Enter para iniciar el sistema...")

def save_to_env(key, value):
    """Saves a key-value pair to config/.env securely."""
    env_path = "config/.env"
    
    # Ensure config dir exists
    if not os.path.exists("config"):
        os.makedirs("config")
        
    env_vars = {}
    
    # Read existing
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    env_vars[k] = v
    
    # Update
    env_vars[key] = value
        
    # Write back
    with open(env_path, "w") as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")

def update_settings_provider(provider_name, model_name):
    """Updates config/settings.json to match the new provider."""
    import json
    
    settings_file = "config/settings.json"
    data = {}
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as f:
                data = json.load(f)
        except:
            pass
    
    if "ai_providers" not in data:
        data["ai_providers"] = {}
        
    if provider_name not in data["ai_providers"]:
        data["ai_providers"][provider_name] = {}
        
    data["ai_providers"][provider_name]["model"] = model_name
    data["active_provider"] = provider_name
    
    with open(settings_file, "w") as f:
        json.dump(data, f, indent=4)
