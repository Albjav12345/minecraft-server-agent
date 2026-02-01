import os
import hashlib
import requests
import json
from typing import List, Dict, Any
from src.managers.instance_manager import InstanceManager
from src.api.minecraft_api import validator
import src.core.ui as ui

class MigrationManager:
    # AHORA ACEPTAMOS root_path EXPLÍCITAMENTE
    def __init__(self, instance_manager: InstanceManager, root_path: str = None):
        self.im = instance_manager
        self.modrinth_base = "https://api.modrinth.com/v2"
        
        # Estrategia de Resolución de Ruta:
        # 1. Usar la que nos pasan explícitamente (Prioridad)
        if root_path:
            self.root_path = root_path
        else:
            # 2. Fallback: Intentar adivinar (Solo por retrocompatibilidad)
            self.root_path = getattr(self.im, 'instances_path', 
                             getattr(self.im, 'root_path', 
                             getattr(self.im, 'base_path', None)))
                         
        if not self.root_path:
             # 3. Fallback metodo
             if hasattr(self.im, 'get_instances_path'):
                 self.root_path = self.im.get_instances_path()

    def get_file_sha1(self, file_path: str) -> str:
        sha1 = hashlib.sha1()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data: break
                sha1.update(data)
        return sha1.hexdigest()

    def identify_mods(self, mod_paths: List[str]) -> Dict[str, str]:
        hashes = []
        hash_to_path = {}
        for path in mod_paths:
            h = self.get_file_sha1(path)
            hashes.append(h)
            hash_to_path[h] = path

        if not hashes: return {}

        try:
            response = requests.post(
                f"{self.modrinth_base}/version_files",
                json={"hashes": hashes, "algorithm": "sha1"},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code != 200:
                ui.console.print(f"[dim red]⚠ Modrinth API Error: {response.status_code}[/dim red]")
                return {}
            
            data = response.json()
            return {h: info["project_id"] for h, info in data.items()}
        except Exception as e:
            ui.console.print(f"[dim red]⚠ Error de red identificando mods: {e}[/dim red]")
            return {}

    def migrate_profile(self, source_name: str, new_name: str, target_version: str) -> Dict[str, Any]:
        report = {"source": source_name, "target": target_version, "success": [], "failed": [], "error": None}
        
        # 0. Safety Check
        if not self.root_path:
            report["error"] = "CRITICAL: Ruta raíz no definida en MigrationManager."
            return report

        try:
            # 1. Validar Origen
            source_mods_path = os.path.join(self.root_path, source_name, "mods")
            
            if not os.path.exists(source_mods_path):
                # Fallback para estructuras Legacy (.minecraft)
                legacy_path = os.path.join(self.root_path, source_name, ".minecraft", "mods")
                if os.path.exists(legacy_path):
                    source_mods_path = legacy_path
                else:
                    report["error"] = f"No se encuentra carpeta 'mods' en: {source_mods_path}"
                    return report

            # 2. Escanear
            ui.console.print(f"[cyan]🔍 Escaneando: {source_mods_path}[/cyan]")
            mod_files = [os.path.join(source_mods_path, f) for f in os.listdir(source_mods_path) if f.endswith(".jar")]
            
            if not mod_files:
                report["error"] = "Carpeta de mods vacía."
                return report

            # 3. Identificar
            ui.console.print(f"[cyan]📡 Identificando {len(mod_files)} mods...[/cyan]")
            project_map = self.identify_mods(mod_files)
            
            if not project_map:
                ui.console.print("[yellow]⚠ No se pudo identificar ningún mod. ¿Mods oficiales?[/yellow]")
            else:
                ui.console.print(f"[dim]✔ {len(project_map)} mods identificados.[/dim]")

            # 4. Crear Instancia (Usando nombre limpio)
            # new_name podría venir sucio, lo limpiamos si es necesario o confiamos en IM
            ui.console.print(f"[cyan]✨ Creando perfil '{new_name}'...[/cyan]")
            success, msg, _ = self.im.create_instance(new_name, target_version, "fabric")
            if not success:
                report["error"] = msg
                return report

            # 5. Migrar
            ui.console.print(f"[cyan]🔄 Instalando versiones para {target_version}...[/cyan]")
            for h, pid in project_map.items():
                dl = validator.get_mod_download(pid, target_version, "fabric")
                if dl:
                    ui.console.print(f"  [green]✔ {dl['filename']}[/green]")
                    ok, _ = self.im.install_mod(new_name, dl['url'], dl['filename'])
                    if ok: report["success"].append({"name": pid, "file": dl["filename"]})
                    else: report["failed"].append({"name": pid, "reason": "Error Disco"})
                else:
                    ui.console.print(f"  [red]❌ Incompatible (ID: {pid})[/red]")
                    report["failed"].append({"name": pid, "reason": "Incompatible"})
            
            return report

        except Exception as e:
            ui.console.print(f"[bold red]CRASH: {e}[/bold red]")
            import traceback
            traceback.print_exc()
            report["error"] = str(e)
            return report
