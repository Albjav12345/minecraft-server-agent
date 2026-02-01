import json
import os
import src.core.ui as ui
from typing import Dict, List, Optional

BRAIN_FILE = "brain.json"

class MemoryManager:
    def __init__(self):
        self.data = {
            "instances": {},        # {name: {path, version, loader, mods: []}}
            "active_instance": None,
            "user_profile": {
                "preferences": []
            },
            "history": []           # Last N chat messages
        }
        self.load_memory()

    def load_memory(self):
        if os.path.exists(BRAIN_FILE):
            try:
                with open(BRAIN_FILE, 'r') as f:
                    self.data = json.load(f)
            except Exception as e:
                ui.print_error_panel(f"Error cargando memoria: {e}")

    def save_memory(self):
        try:
            with open(BRAIN_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            ui.print_error_panel(f"Error guardando memoria: {e}")

    # --- Instance Management ---
    def register_instance(self, name: str, version: str, loader: str, path: str):
        self.data["instances"][name] = {
            "path": path,
            "version": version,
            "loader": loader,
            "mods": []
        }
        self.set_active_instance(name)
        self.save_memory()

    def get_instance(self, name: str) -> Optional[Dict]:
        return self.data["instances"].get(name)

    def get_all_instances(self) -> Dict:
        return self.data["instances"]

    def set_active_instance(self, name: str):
        if name in self.data["instances"]:
            self.data["active_instance"] = name
            self.save_memory()
            return True
        return False

    def get_active_instance_data(self) -> Optional[Dict]:
        active = self.data.get("active_instance")
        if active:
            return self.data["instances"].get(active)
        return None
    
    def get_active_instance_name(self) -> Optional[str]:
        return self.data.get("active_instance")

    # --- Mod Tracking ---
    def add_installed_mod(self, mod_name: str, version: str):
        active_name = self.get_active_instance_name()
        if active_name:
            if "mods" not in self.data["instances"][active_name]:
                 self.data["instances"][active_name]["mods"] = []
            
            # Check if exists
            mods = self.data["instances"][active_name]["mods"]
            for m in mods:
                if m["name"] == mod_name:
                    m["version"] = version # Update version
                    self.save_memory()
                    return

            mods.append({"name": mod_name, "version": version})
            self.save_memory()

    # --- History & Context ---
    def add_history(self, role: str, content: str):
        self.data["history"].append({"role": role, "content": content})
        # Keep last 10 messages
        if len(self.data["history"]) > 10:
            self.data["history"].pop(0)
        self.save_memory()

    def get_chat_history(self) -> List[Dict]:
        return self.data.get("history", [])

    def get_system_context(self) -> str:
        ctx = "ESTADO ACTUAL:\n"
        active = self.get_active_instance_data()
        if active:
            ctx += f"- Instancia Activa: {self.data['active_instance']}\n"
            ctx += f"- Versión Minecraft: {active.get('version')}\n"
            ctx += f"- Loader: {active.get('loader')}\n"
            ctx += f"- Mods Instalados ({len(active.get('mods', []))}): {', '.join([m['name'] for m in active.get('mods', [])])}\n"
        else:
            ctx += "- No hay instancia seleccionada.\n"
        
        ctx += "\nPREFERENCIAS DE USUARIO:\n"
        prefs = self.data["user_profile"].get("preferences", [])
        if prefs:
            ctx += "\n".join(f"- {p}" for p in prefs)
        else:
            ctx += "- Sin preferencias registradas."
            
        return ctx
