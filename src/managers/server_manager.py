"""
MineGenesis V6.0 - Server Manager
Dedicated Server Management (for hosting multiplayer servers).
Handles server JAR downloads, EULA acceptance, and startup script generation.
"""
import os
import json
import requests
import subprocess
import time
from typing import List, Dict, Optional, Tuple
from src.api.minecraft_api import validator, get_server_jar_url

class ServerManager:
    """Manages DEDICATED Minecraft servers (for hosting)."""
    
    def __init__(self, root_path: str):
        self.root = root_path
    
    def validate_path(self) -> bool:
        """Ensures the root path exists."""
        if not os.path.exists(self.root):
            try:
                os.makedirs(self.root)
                return True
            except Exception as e:
                print(f"Error creating path: {e}")
                return False
        return True
    
    def get_servers(self) -> List[Dict]:
        """
        Scans for dedicated server folders.
        
        Detection criteria:
        - Has server.jar OR
        - Has server.properties OR
        - Has metadata.json from us
        
        Returns list of dicts:
        {
            'name': str,
            'type': 'Managed' | 'Detected',
            'path': str,
            'version': str or '?',
            'server_type': 'vanilla' | 'paper' | 'fabric',
            'status': 'OFFLINE' | 'ONLINE',
            'port': int
        }
        """
        if not os.path.exists(self.root):
            return []
        
        servers = []
        
        for item in os.listdir(self.root):
            folder_path = os.path.join(self.root, item)
            
            if not os.path.isdir(folder_path):
                continue
            
            # Check if it's a server
            has_jar = os.path.exists(os.path.join(folder_path, "server.jar"))
            has_properties = os.path.exists(os.path.join(folder_path, "server.properties"))
            
            if not (has_jar or has_properties):
                continue
            
            # Try to read our metadata
            meta_file = os.path.join(folder_path, "metadata.json")
            
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    
                    servers.append({
                        'name': meta.get('name', item),
                        'type': 'Managed',
                        'path': folder_path,
                        'version': meta.get('version', '?'),
                        'server_type': meta.get('server_type', 'unknown'),
                        'status': self._get_status(folder_path),
                        'port': self._get_port(folder_path)
                    })
                except:
                    pass
            
            # If no metadata, it's detected
            if not any(srv['name'] == item for srv in servers):
                servers.append({
                    'name': item,
                    'type': 'Detected',
                    'path': folder_path,
                    'version': '?',
                    'server_type': 'unknown',
                    'status': self._get_status(folder_path),
                    'port': self._get_port(folder_path)
                })
        
        return servers
    
    def _get_status(self, server_path: str) -> str:
        """Checks if server is running (basic check)."""
        # Simple check: look for .pid file or running process
        # For now, always return OFFLINE (real implementation would check processes)
        return "OFFLINE"
    
    def _get_port(self, server_path: str) -> int:
        """Reads port from server.properties."""
        props_file = os.path.join(server_path, "server.properties")
        
        if os.path.exists(props_file):
            try:
                with open(props_file, 'r') as f:
                    for line in f:
                        if line.startswith("server-port="):
                            return int(line.split("=")[1].strip())
            except:
                pass
        
        return 25565  # Default
    
    def create_dedicated_server(self, name: str, version: str, server_type: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Creates a dedicated server with SMART defaults.
        If server_type is None -> defaults to 'fabric' (standard) or 'vanilla' based on context.
        """
        # Smart Default: Fabric is the modern standard for modding
        if not server_type:
            server_type = "fabric"
            
        # 1. Validate version
        is_valid, error_msg = validator.validate_version(version)
        if not is_valid:
            return False, error_msg, None
        
        # 2. Sanitize name and create path
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-', '.')).strip()
        if not safe_name:
            return False, "❌ Nombre inválido", None
        
        server_path = os.path.join(self.root, safe_name)
        
        if os.path.exists(server_path):
            return False, f"❌ El servidor '{safe_name}' ya existe", None
        
        try:
            # Create base folder
            os.makedirs(server_path)
            
            # 3. Download server.jar
            jar_url = self._get_server_jar_url(version, server_type)
            if not jar_url:
                # Fallback to vanilla if fabric/paper fail
                if server_type != "vanilla":
                    print(f"⚠ No JAR for {server_type} {version}, falling back to Vanilla.")
                    server_type = "vanilla"
                    jar_url = self._get_server_jar_url(version, "vanilla")
                
                if not jar_url:
                     return False, f"❌ No se pudo obtener URL para {version}", None
            
            jar_path = os.path.join(server_path, "server.jar")
            
            response = requests.get(jar_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(jar_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 4. Create eula.txt
            eula_path = os.path.join(server_path, "eula.txt")
            with open(eula_path, 'w') as f:
                f.write("# Auto-generated by MineGenesis\neula=true\n")
            
            # 5. Generate start scripts
            self._create_start_scripts(server_path)
            
            # 6. Create server.properties
            self._create_server_properties(server_path)
            
            # 7. Create folders
            if server_type in ['paper', 'spigot', 'bukkit']:
                os.makedirs(os.path.join(server_path, "plugins"))
            else:
                os.makedirs(os.path.join(server_path, "mods"))
            
            os.makedirs(os.path.join(server_path, "world"))
            
            # 8. Create metadata
            meta = {
                "name": safe_name,
                "version": version,
                "server_type": server_type,
                "created": "now",
                "type": "dedicated_server"
            }
            
            with open(os.path.join(server_path, "metadata.json"), 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=4)
            
            return True, f"✔ Servidor '{safe_name}' ({server_type}) creado.", server_path
            
        except Exception as e:
            return False, f"❌ Error: {e}", None

    def install_plugin(self, server_name: str, url: str, filename: str, mod_id: str = None) -> Tuple[bool, str]:
        """
        Downloads and installs a plugin/mod with SAFETY CHECKS.
        """
        from mod_intelligence import intelligence
        
        servers = self.get_servers()
        server = next((s for s in servers if s['name'] == server_name), None)
        
        if not server:
            return False, f"❌ Servidor '{server_name}' no encontrado"
        
        # Determine folder (plugins or mods)
        server_type = server.get('server_type', 'unknown')
        folder_name = "plugins" if server_type in ['paper', 'spigot', 'bukkit'] else "mods"
        
        # INTELLIGENCE CHECK
        if mod_id:
            from src.ai.mod_intelligence import intelligence
            action, reason = intelligence.analyze_mod_compatibility(mod_id, "server")
            if action == "BLOCK":
                return False, f"⛔ BLOCKED: {reason}"
            if action == "WARN":
                print(f"[yellow]⚠ WARNING: {reason}[/yellow]")
        
        plugins_path = os.path.join(server['path'], folder_name)
        
        if not os.path.exists(plugins_path):
            os.makedirs(plugins_path)
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            file_path = os.path.join(plugins_path, filename)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True, f"✔ Mod/Plugin '{filename}' instalado en {server_name}"
            
        except Exception as e:
            return False, f"❌ Error descargando: {e}"
