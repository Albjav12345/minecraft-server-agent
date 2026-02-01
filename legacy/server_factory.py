"""
Server Factory V4.0
Exports server-ready artifacts from client instances.
Filters client-only mods automatically.
"""
import os
import shutil
from typing import Dict
from instance_manager import InstanceManager
import minecraft_ops

# Client-only mods that crash servers
CLIENT_ONLY_MODS = [
    "sodium", "iris", "optifine", "optifabric",
    "modmenu", "emi", "rei", "jei",
    "xaeros-minimap", "xaeros-worldmap", "journeymap",
    "lambdynamiclights", "zoomify", "logical-zoom",
    "wthit", "jade", "hwyla",
    "bobby", "farsight", "distant-horizons",
    "roughly-enough-items", "cloth-config", "architectury"
]

class ServerFactory:
    def __init__(self, instance_manager: InstanceManager):
        self.im = instance_manager
    
    def _is_client_only(self, filename: str) -> bool:
        """Checks if mod filename matches client-only blacklist."""
        filename_lower = filename.lower()
        return any(client_mod in filename_lower for client_mod in CLIENT_ONLY_MODS)
    
    def export_server(self, instance_name: str, server_name: str = None) -> Dict:
        """
        Creates a server build from client instance.
        
        Steps:
        1. Validate source instance exists
        2. Create server folder structure
        3. Copy & filter mods
        4. Copy configs
        5. Download server.jar
        6. Generate eula.txt + start script
        
        Returns: {"status": "success"|"error", "message": str}
        """
        meta = self.im.get_instance_meta(instance_name)
        if not meta:
            return {"status": "error", "message": f"Instancia '{instance_name}' no encontrada."}
        
        # Generate server name
        if not server_name:
            server_name = f"{instance_name}_Server"
        
        server_path = os.path.join(self.im.root, "_SERVERS", server_name)
        
        if os.path.exists(server_path):
            return {"status": "error", "message": f"El servidor '{server_name}' ya existe."}
        
        try:
            # Create structure
            os.makedirs(server_path)
            os.makedirs(os.path.join(server_path, "mods"))
            os.makedirs(os.path.join(server_path, "config"))
            
            # Copy configs
            src_config = os.path.join(self.im.get_instance_path(instance_name), "config")
            if os.path.exists(src_config):
                shutil.copytree(src_config, os.path.join(server_path, "config"), dirs_exist_ok=True)
            
            # Copy & Filter Mods
            mods = self.im.list_mods(instance_name)
            copied = 0
            skipped = 0
            
            for mod in mods:
                if self._is_client_only(mod):
                    skipped += 1
                    continue
                
                src = os.path.join(self.im.get_instance_path(instance_name), "mods", mod)
                dst = os.path.join(server_path, "mods", mod)
                shutil.copy2(src, dst)
                copied += 1
            
            # Download server core
            loader = meta["loader"]
            version = meta["version"]
            
            ok, msg = minecraft_ops.download_server_jar(loader, version, server_path)
            if not ok:
                return {"status": "error", "message": f"Error descargando server.jar: {msg}"}
            
            # EULA
            with open(os.path.join(server_path, "eula.txt"), "w") as f:
                f.write("eula=true\n")
            
            # Start script
            with open(os.path.join(server_path, "START.bat"), "w") as f:
                f.write("@echo off\n")
                f.write("java -Xmx4G -jar server.jar nogui\n")
                f.write("pause\n")
            
            return {
                "status": "success",
                "message": f"✓ Servidor creado: {server_path}\n✓ Mods: {copied} copiados, {skipped} filtrados (client-only)"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Error: {e}"}
