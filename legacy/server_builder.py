import os
import shutil
import ui
import minecraft_ops
from instance_manager import InstanceManager

# Blacklist of client-side only mods that crash servers
CLIENT_MODS_BLACKLIST = [
    "sodium", "iris", "reeses-sodium-options", "sodium-extra",
    "modmenu", "reis-minimap", "xaeros-minimap", "xaeros-worldmap",
    "lambdynamiclights", "zoomify", "wthit", "jade", "emi", "rei", "jei" 
    # Note: REI/JEI/EMI are sometimes server-side optional but safe to exclude for pure vanilla servers
]

class ServerBuilder:
    def __init__(self, instance_manager: InstanceManager):
        self.im = instance_manager

    def create_server_from_instance(self, instance_name: str, output_folder_name: str = None) -> dict:
        """
        Builds a deployable server artifact from a client instance.
        1. Copies mods (filtering client-only ones).
        2. Copies config.
        3. Downloads server core (server.jar).
        4. Generates eula.txt.
        """
        src_path = self.im.get_instance_path(instance_name)
        meta = self.im.get_instance_meta(instance_name)
        
        if not meta:
            return {"status": "error", "message": "Instancia no encontrada."}
            
        build_name = output_folder_name or f"{instance_name}_Server_Build"
        dest_path = os.path.join(self.im.root_path, "_SERVERS", build_name)
        
        if os.path.exists(dest_path):
            return {"status": "error", "message": f"Ya existe un build en {dest_path}"}
            
        try:
            ui.print_system_msg("Iniciando construcción del servidor...", "info")
            
            # 1. Create Structure
            os.makedirs(dest_path)
            os.makedirs(os.path.join(dest_path, "mods"))
            os.makedirs(os.path.join(dest_path, "config"))
            
            # 2. Copy Configs (Usually safe)
            src_config = os.path.join(src_path, "config")
            if os.path.exists(src_config):
                shutil.copytree(src_config, os.path.join(dest_path, "config"), dirs_exist_ok=True)
                
            # 3. Copy & Filter Mods
            src_mods = os.path.join(src_path, "mods")
            if os.path.exists(src_mods):
                copied_count = 0
                skipped_count = 0
                for mod_file in os.listdir(src_mods):
                    if not mod_file.endswith(".jar"): continue
                    
                    # Filtering Logic
                    mod_lower = mod_file.lower()
                    is_blacklisted = any(bad in mod_lower for bad in CLIENT_MODS_BLACKLIST)
                    
                    if is_blacklisted:
                        skipped_count += 1
                        continue
                        
                    shutil.copy2(os.path.join(src_mods, mod_file), os.path.join(dest_path, "mods"))
                    copied_count += 1
                
                ui.print_system_msg(f"Mods procesados: {copied_count} copiados, {skipped_count} ignorados (Client-side).", "success")

            # 4. Download Core
            loader = meta["loader"]
            version = meta["version"]
            
            ok, msg = minecraft_ops.download_server_jar(loader, version, dest_path)
            if not ok:
                 return {"status": "error", "message": f"Fallo bajando server core: {msg}"}
                 
            # 5. EULA
            with open(os.path.join(dest_path, "eula.txt"), "w") as f:
                f.write("eula=true")
            
            # 6. Server Properties (Template)
            with open(os.path.join(dest_path, "server.properties"), "w") as f:
                f.write(f"motd=Server generated from {instance_name} by MineGenesis\n")
            
            # 7. Start Script (Windows)
            with open(os.path.join(dest_path, "START_SERVER.bat"), "w") as f:
                f.write("java -Xmx4G -jar server.jar nogui\npause")
                
            return {"status": "success", "message": f"Servidor listo en: {dest_path}"}

        except Exception as e:
            return {"status": "error", "message": f"Build fallido: {e}"}
