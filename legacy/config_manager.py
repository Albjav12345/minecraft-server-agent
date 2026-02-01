import os
import json
import webbrowser
from typing import Optional, Dict
from dotenv import load_dotenv, set_key
import ui

DOCS_URLS = {
    "groq": "https://console.groq.com/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys"
}

CONFIG_FILE = "config.json"
ENV_FILE = ".env"

class ConfigManager:
    def __init__(self):
        load_dotenv(ENV_FILE)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_current_model(self) -> Optional[str]:
        return self.config.get("current_model")

    def set_current_model(self, model: str):
        self.config["current_model"] = model
        self._save_config()

    def get_api_key(self, model: str) -> Optional[str]:
        env_key = f"{model.upper()}_API_KEY"
        return os.getenv(env_key)

    def ensure_configured(self):
        """Runs the wizard if no model is selected or the selected model is missing a key."""
        current = self.get_current_model()
        
        if not current:
            ui.print_banner()
            ui.print_system_msg("Iniciando secuencia de configuración inicial...", "highlight")
            self._run_model_selection_wizard()
        elif not self.get_api_key(current):
            ui.print_system_msg(f"Falta la configuración de credenciales para: {current}", "warning")
            self._run_credential_wizard(current)

    def switch_model(self, model_name: str):
        valid_models = ["groq", "gemini", "openai", "anthropic"]
        if model_name not in valid_models:
            ui.print_error_panel(f"Modelo desconocido: {model_name}\nOpciones válidas: {', '.join(valid_models)}")
            return

        ui.print_step(f"Cambiando núcleo de procesamiento a: {model_name.upper()}...")
        if not self.get_api_key(model_name):
            if ui.confirm_action(f"No se detectó API Key para {model_name}. ¿Configurar ahora?"):
                self._run_credential_wizard(model_name)
            else:
                ui.print_system_msg("Cambio de modelo abortado.", "error")
                return
        
        self.set_current_model(model_name)
        ui.print_success(f"Sistema reconfigurado. Motor activo: {model_name.upper()}")

    def _run_model_selection_wizard(self):
        ui.print_panel("[1] Groq (Recomendado - Llama 3)\n[2] Google Gemini\n[3] OpenAI (GPT-4)\n[4] Anthropic (Claude)", title="SELECCIONA TU MOTOR DE IA")
        
        choice = ui.ask_user("Selecciona una opción [1-4]")
        model_map = {"1": "groq", "2": "gemini", "3": "openai", "4": "anthropic"}
        
        selected = model_map.get(choice)
        if not selected:
            ui.print_system_msg("Opción inválida. Seleccionando Groq por defecto.", "warning")
            selected = "groq"
        
        self.set_current_model(selected)
        self._run_credential_wizard(selected)

    def _run_credential_wizard(self, model: str):
        ui.print_panel(f"Configurando acceso para: {model.upper()}", title="WIZARD DE SEGURIDAD")
        
        if ui.confirm_action("¿Deseas abrir la página oficial para obtener tu API Key?"):
            url = DOCS_URLS.get(model)
            if url:
                ui.print_system_msg(f"Abriendo enlace al netrunner... {url}")
                webbrowser.open(url)
            else:
                ui.print_system_msg("No hay URL conocida para este proveedor.", "error")

        api_key = ui.ask_user(f"Introduce tu {model.upper()}_API_KEY", password=False)
        
        if api_key.strip():
            # Save to .env using 'key' instead of 'dotenv_key' for set_key as per some versions, 
            # but standard python-dotenv set_key usage is set_key(dotenv_path, key_to_set, value_to_set)
            # Create .env if not exists
            if not os.path.exists(ENV_FILE):
                open(ENV_FILE, 'w').close()
            
            set_key(ENV_FILE, f"{model.upper()}_API_KEY", api_key)
            os.environ[f"{model.upper()}_API_KEY"] = api_key # Update runtime env
            ui.print_success("Credenciales encriptadas y almacenadas con éxito.")
        else:
            ui.print_error_panel("Clave vacía. La configuración ha fallado.")

