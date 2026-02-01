"""
MineGenesis V6.0 - Instance Manager
CLIENT-ONLY instance management (for playing Minecraft).
Dedicated servers are handled by server_manager.py.
"""
import os
import json
from typing import List, Dict, Optional, Tuple
from src.api.minecraft_api import validator

class InstanceManager:
    """Manages CLIENT Minecraft instances (profiles for playing)."""
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
    
    def get_instances(self) -> List[Dict]:
        """
        Scans for client instances.
        
        Detection criteria:
        - Has instance.json (Managed) OR
        - Has mods/, saves/, or options.txt (Detected)
        
        Returns list of dicts with: name, type, version, mods
        """
        if not os.path.exists(self.root):
            return []
        
        instances = []
        
        for item in os.listdir(self.root):
            folder_path = os.path.join(self.root, item)
            
            if not os.path.isdir(folder_path):
                continue
            
            # Check if it's an instance
            has_metadata = os.path.exists(os.path.join(folder_path, "instance.json"))
            has_mods = os.path.exists(os.path.join(folder_path, "mods"))
            has_saves = os.path.exists(os.path.join(folder_path, "saves"))
            has_options = os.path.exists(os.path.join(folder_path, "options.txt"))
            
            if not (has_metadata or has_mods or has_saves or has_options):
                continue
            
            # Try to read metadata
            meta_file = os.path.join(folder_path, "instance.json")
            
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    
                    # Count mods
                    mods_dir = os.path.join(folder_path, "mods")
                    mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')]) if os.path.exists(mods_dir) else 0
                    
                    instances.append({
                        'name': meta.get('name', item),
                        'type': 'Managed',
                        'path': folder_path,
                        'version': meta.get('version', '?'),
                        'mods': mod_count
                    })
                except:
                    pass
            
            # If no metadata, it's detected
            if not any(inst['name'] == item for inst in instances):
                # Try to guess version from folder name
                version = '?'
                for part in item.split('_'):
                    if '.' in part and part[0].isdigit():
                        version = part
                        break
                
                # Count mods
                mods_dir = os.path.join(folder_path, "mods")
                mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')]) if os.path.exists(mods_dir) else 0
                
                instances.append({
                    'name': item,
                    'type': 'Detected',
                    'path': folder_path,
                    'version': version,
                    'mods': mod_count
                })
        
        return instances

    
    def create_instance(self, name: str, version: str, loader: str) -> Tuple[bool, str, Optional[str]]:
        """
        Creates a new Minecraft instance with STRICT validation.
        
        Validation order:
        1. Check version exists (Mojang API)
        2. Check loader compatibility
        3. Check if instance already exists
        4. Create folder structure
        
        Returns: (success: bool, message: str, created_name: Optional[str])
        """
        # VALIDATION 1: Version exists?
        is_valid, error_msg = validator.validate_version(version)
        if not is_valid:
            return False, error_msg, None
        
        # VALIDATION 2: Loader valid?
        loader_ok, loader_msg = validator.get_loader_info(version, loader)
        if not loader_ok:
            return False, loader_msg, None
        
        # VALIDATION 3: Sanitize name
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-', '.')).strip()
        if not safe_name:
            return False, "❌ Nombre de instancia inválido", None
        
        # VALIDATION 4: Already exists?
        path = os.path.join(self.root, safe_name)
        if os.path.exists(path):
            return False, f"❌ La instancia '{safe_name}' ya existe", None
        
        # CREATE STRUCTURE
        try:
            os.makedirs(path)
            os.makedirs(os.path.join(path, "mods"))
            os.makedirs(os.path.join(path, "config"))
            os.makedirs(os.path.join(path, "resourcepacks"))
            os.makedirs(os.path.join(path, "shaderpacks"))
            os.makedirs(os.path.join(path, "saves"))
            
            # Create metadata
            meta = {
                "name": safe_name,
                "version": version,
                "loader": loader,
                "created": "now",
                "type": "client_instance"
            }
            
            with open(os.path.join(path, "instance.json"), 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=4)
            
            return True, f"✓ Instancia '{safe_name}' creada para Minecraft {version} ({loader})", safe_name
            
        except Exception as e:
            return False, f"❌ Error creando instancia: {e}", None
    
    def install_mod(self, instance_name: str, url: str, filename: str) -> Tuple[bool, str]:
        """Downloads and installs a mod .jar file into an instance."""
        import requests
        path = self.get_path(instance_name)
        if not path:
            return False, f"❌ Instancia '{instance_name}' no encontrada"
            
        mods_path = os.path.join(path, "mods")
        if not os.path.exists(mods_path):
            os.makedirs(mods_path)
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            file_path = os.path.join(mods_path, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True, f"✓ Mod '{filename}' instalado"
        except Exception as e:
            return False, f"❌ Error descargando mod: {e}"

    def get_path(self, instance_name: str) -> Optional[str]:
        """Resolves instance name to its folder path."""
        for item in os.listdir(self.root):
            path = os.path.join(self.root, item)
            if not os.path.isdir(path): continue
            
            # Check instance.json name
            meta_file = os.path.join(path, "instance.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    if meta.get('name') == instance_name:
                        return path
                except: pass
            
            # Check folder name
            if item == instance_name:
                return path
        return None

    def get_mod_list(self, instance_name: str) -> List[str]:
        """Returns a list of .jar filenames in the mods folder of an instance."""
        path = self.get_path(instance_name)
        if not path:
            return []
            
        mods_path = os.path.join(path, "mods")
        if not os.path.exists(mods_path):
            return []
        
        try:
            return [f for f in os.listdir(mods_path) if f.endswith('.jar')]
        except Exception:
            return []
