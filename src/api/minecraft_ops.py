import os
import requests
import src.core.ui as ui

# NOTE: Functions now require 'server_path' argument to support multi-instance isolation.

def download_server_jar(software: str, version: str, server_path: str):
    if not server_path or not os.path.exists(server_path):
        return False, "Ruta de instancia inválida."

    filename = "server.jar"
    url = ""
    
    with ui.show_spinner(f"Obteniendo enlace de descarga para {software} {version}..."):
        if software.lower() == "paper":
            try:
                base_api = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
                resp = requests.get(base_api)
                if resp.status_code != 200:
                    raise Exception("Versión no encontrada")
                builds = resp.json()["builds"]
                latest_build = builds[-1]
                url = f"{base_api}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
            except Exception as e:
                return False, str(e)

        elif software.lower() == "fabric":
            try:
                # Fabric requires installer or jar. For server jar:
                url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/0.15.11/server/jar"
            except:
                return False, "Error construyendo URL Fabric"
        
        else: 
            return False, "Soporte Vanilla limitado en esta versión."

    # Download
    try:
        ui.print_step(f"Descargando {filename} en {server_path}...")
        response = requests.get(url, stream=True)
        path = os.path.join(server_path, filename)
        
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # Ensure eula (redundant if instance_manager did it, but safe)
        with open(os.path.join(server_path, "eula.txt"), "w") as f:
            f.write("eula=true")
            
        return True, f"Core instalado."
    except Exception as e:
        return False, f"Error de descarga: {e}"

def read_properties(server_path: str) -> str:
    if not server_path: return "No instance selected."
    prop_path = os.path.join(server_path, "server.properties")
    if os.path.exists(prop_path):
        with open(prop_path, 'r') as f:
            return f.read()
    return "No server.properties found."

def list_mods(server_path: str):
    if not server_path: return []
    mods_path = os.path.join(server_path, "mods")
    if os.path.exists(mods_path):
        return os.listdir(mods_path)
    return []

def install_mod_file(url: str, filename: str, server_path: str):
    if not server_path: return False
    mods_path = os.path.join(server_path, "mods")
    os.makedirs(mods_path, exist_ok=True)
    try:
        resp = requests.get(url)
        with open(os.path.join(mods_path, filename), 'wb') as f:
            f.write(resp.content)
        return True
    except:
        return False
