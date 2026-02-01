"""
MineGenesis V4.0 - Settings Manager
Manages persistent configuration with strict path validation.
"""
import os
import json
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()

class Settings:
    def __init__(self):
        """Initialize settings from JSON and .env files."""
        self.config_file = "config/settings.json"
        
        # Force reload .env to get latest API keys
        from dotenv import load_dotenv
        env_path = os.path.abspath("config/.env")
        loaded = load_dotenv(env_path, override=True)
        
        # Debug .env loading - remove later
        # console.print(f"[dim]Debug: Loading .env from {env_path}[/dim]")
        # console.print(f"[dim]Debug: load_dotenv returned {loaded}[/dim]")
        # console.print(f"[dim]Debug: GROQ_API_KEY in env: {os.getenv('GROQ_API_KEY') is not None}[/dim]")
        
        # Default structure with API keys from environment
        self.data = {
            "instances_path": None,
            "last_instance": None,
            "servers_path": None,
            "last_server": None,
            "ai_providers": {
                "groq": {"api_key": os.getenv("GROQ_API_KEY"), "model": "llama-3.3-70b-versatile"},
                "google gemini": {"api_key": os.getenv("GEMINI_API_KEY"), "model": "gemini-pro"},
                "openai": {"api_key": os.getenv("OPENAI_API_KEY"), "model": "gpt-4-turbo"},
                "anthropic": {"api_key": os.getenv("ANTHROPIC_API_KEY"), "model": "claude-3-5-sonnet-20240620"}
            },
            "active_provider": "groq"
        }
        self.load()

    def _load_env(self):
        """Manually loads .env file."""
        env_path = "config/.env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value
    
    def load(self):
        """Load settings from JSON file and migrate old keys."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    
                    # Migration: "groq_api_key" -> "ai_providers"
                    if "groq_api_key" in loaded and loaded["groq_api_key"]:
                        if "ai_providers" not in loaded:
                            loaded["ai_providers"] = {}
                        if "groq" not in loaded["ai_providers"]:
                            loaded["ai_providers"]["groq"] = {}
                        loaded["ai_providers"]["groq"]["api_key"] = loaded.pop("groq_api_key")
                    
                    # Migration: "llm_provider" -> "active_provider"
                    if "llm_provider" in loaded:
                        loaded["active_provider"] = loaded.pop("llm_provider")

                    # CRITICAL: Merge ai_providers intelligently
                    # We MUST NOT trust api_key from JSON, only from .env (constructor)
                    if "ai_providers" in loaded:
                        for provider, config in loaded["ai_providers"].items():
                            if provider in self.data["ai_providers"]:
                                # Merge: ignore api_key from file, keep the one from .env
                                config.pop("api_key", None) 
                                self.data["ai_providers"][provider].update(config)
                            else:
                                # New provider from file - also strip api_key just in case
                                config.pop("api_key", None)
                                self.data["ai_providers"][provider] = config
                        
                        # Remove ai_providers from loaded to avoid overwrite
                        del loaded["ai_providers"]
                    
                    # Now update the rest safely
                    self.data.update(loaded)
                    
                    # Ensure struct integrity
                    if "ai_providers" not in self.data:
                         self.data["ai_providers"] = {}
                    
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load settings: {e}[/yellow]")
    
    def get_provider_config(self, provider_name: str) -> dict:
        """Get config for a specific provider."""
        return self.data["ai_providers"].get(provider_name, {})

    def set_provider_config(self, provider_name: str, api_key: str, model: str = None):
        """Set config for a provider."""
        if provider_name not in self.data["ai_providers"]:
            self.data["ai_providers"][provider_name] = {}
        
        self.data["ai_providers"][provider_name]["api_key"] = api_key
        if model:
            self.data["ai_providers"][provider_name]["model"] = model
        self.save()

    def get_active_provider(self) -> str:
        """Get the currently active provider name."""
        return self.data.get("active_provider", "groq")

    def set_active_provider(self, provider_name: str):
        """Set the active provider."""
        self.data["active_provider"] = provider_name
        self.save()
    
    def save(self):
        """Save settings to JSON file, stripping API keys for security and persistence logic."""
        try:
            import copy
            save_data = copy.deepcopy(self.data)
            
            # CRITICAL: Remove all api_key fields before saving to JSON
            if "ai_providers" in save_data:
                for provider in save_data["ai_providers"]:
                    if "api_key" in save_data["ai_providers"][provider]:
                        del save_data["ai_providers"][provider]["api_key"]

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
        except Exception as e:
            console.print(f"[red]Error saving settings: {e}[/red]")
    
    def get_instances_path(self) -> str:
        """Gets/prompts for CLIENT instances path (for playing)."""
        path = self.data.get("instances_path")
        
        while not path or not os.path.isdir(path):
            console.print(Panel(
                "[bold cyan]CONFIGURACIÓN: RUTA DE PERFILES DE CLIENTE[/bold cyan]\n\n"
                "Necesito la ruta donde están tus PERFILES/INSTANCIAS para JUGAR.\n"
                "Ejemplo: C:\\Users\\TuNombre\\Documents\\Minecraft Game\\Profiles",
                title="Client Instances Path",
                border_style="cyan"
            ))
            
            path = Prompt.ask("Ruta de Perfiles de Cliente")
            path = path.strip().strip('\"')
            
            if not os.path.exists(path):
                create = Prompt.ask(
                    f"La ruta no existe. ¿Crear '{path}'?",
                    choices=["s", "n"],
                    default="s"
                )
                if create.lower() == "s":
                    try:
                        os.makedirs(path)
                        console.print(f"[green]✓ Carpeta creada: {path}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error: {e}[/red]")
                        path = None
                else:
                    path = None
        
        self.data["instances_path"] = path
        self.save()
        return path
    
    def get_servers_path(self) -> str:
        """Gets/prompts for DEDICATED SERVERS path (for hosting)."""
        path = self.data.get("servers_path")
        
        while not path or not os.path.isdir(path):
            console.print(Panel(
                "[bold yellow]CONFIGURACIÓN: RUTA DE SERVIDORES DEDICADOS[/bold yellow]\n\n"
                "Necesito la ruta donde se crearán los SERVIDORES DEDICADOS para HOSTEAR.\n"
                "Ejemplo: C:\\Users\\TuNombre\\Documents\\Minecraft Game\\Servers",
                title="Dedicated Servers Path",
                border_style="yellow"
            ))
            
            path = Prompt.ask("Ruta de Servidores Dedicados")
            path = path.strip().strip('\"')
            
            if not os.path.exists(path):
                create = Prompt.ask(
                    f"La ruta no existe. ¿Crear '{path}'?",
                    choices=["s", "n"],
                    default="s"
                )
                if create.lower() == "s":
                    try:
                        os.makedirs(path)
                        console.print(f"[green]✓ Carpeta creada: {path}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error: {e}[/red]")
                        path = None
                else:
                    path = None
        
        self.data["servers_path"] = path
        self.save()
        return path
    
    def get_last_instance(self) -> Optional[str]:
        """Returns last active client instance."""
        return self.data.get("last_instance")
    
    def set_last_instance(self, name: Optional[str]):
        """Sets last active client instance."""
        self.data["last_instance"] = name
        self.save()
    
    def get_last_server(self) -> Optional[str]:
        """Returns last active dedicated server."""
        return self.data.get("last_server")
    
    def set_last_server(self, name: Optional[str]):
        """Sets last active dedicated server."""
        self.data["last_server"] = name
        self.save()
