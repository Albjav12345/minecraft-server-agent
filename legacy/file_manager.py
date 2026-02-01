"""
MineGenesis V5.0 - File Manager
Permissive instance scanning that detects existing Minecraft folders.
"""
import os
import json
from typing import List, Dict, Optional

class FileManager:
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
        PERMISSIVE SCANNING: Detects instances even without our metadata.
        
        Detection criteria:
        - Has mods/ folder OR
        - Has saves/ folder OR  
        - Has options.txt file
        
        Returns list of dicts:
        {
            'name': str,
            'type': 'Managed' | 'Detected',
            'path': str,
            'version': str or '?',
            'mods': int
        }
        """
        if not os.path.exists(self.root):
            return []
        
        instances = []
        
        for item in os.listdir(self.root):
            folder_path = os.path.join(self.root, item)
            
            if not os.path.isdir(folder_path):
                continue
            
            # Check if it's a valid Minecraft instance
            has_mods = os.path.exists(os.path.join(folder_path, "mods"))
            has_saves = os.path.exists(os.path.join(folder_path, "saves"))
            has_options = os.path.exists(os.path.join(folder_path, "options.txt"))
            
            if not (has_mods or has_saves or has_options):
                continue  # Not a Minecraft instance
            
            # Try to read our metadata
            meta_file = os.path.join(folder_path, "instance.json")
            
            if os.path.exists(meta_file):
                # Managed instance
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    
                    instances.append({
                        'name': meta.get('name', item),
                        'type': 'Managed',
                        'path': folder_path,
                        'version': meta.get('version', '?'),
                        'mods': self._count_mods(folder_path)
                    })
                except:
                    pass  # Fall through to detected
            
            # If no metadata, it's a "detected" instance
            if not any(inst['name'] == item for inst in instances):
                instances.append({
                    'name': item,
                    'type': 'Detected',
                    'path': folder_path,
                    'version': self._guess_version(folder_path),
                    'mods': self._count_mods(folder_path)
                })
        
        return instances
    
    def _count_mods(self, instance_path: str) -> int:
        """Counts .jar files in mods folder."""
        mods_path = os.path.join(instance_path, "mods")
        if os.path.exists(mods_path):
            return len([f for f in os.listdir(mods_path) if f.endswith('.jar')])
        return 0
    
    def _guess_version(self, instance_path: str) -> str:
        """
        Tries to guess Minecraft version from folder name.
        E.g., '1.21.8_Fabric' -> '1.21.8'
        """
        folder_name = os.path.basename(instance_path)
        
        # Try to extract version pattern (1.X.X)
        import re
        match = re.search(r'1\.\d+\.?\d*', folder_name)
        if match:
            return match.group(0)
        
        return "?"
    
    def create_instance(self, name: str, version: str, loader: str) -> tuple:
        """
        Creates a new managed instance with full metadata.
        
        Returns: (success: bool, message: str, path: str or None)
        """
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-', '.')).strip()
        if not safe_name:
            return False, "❌ Nombre inválido", None
        
        path = os.path.join(self.root, safe_name)
        
        if os.path.exists(path):
            return False, f"❌ La instancia '{safe_name}' ya existe", None
        
        try:
            # Create structure
            os.makedirs(path)
            os.makedirs(os.path.join(path, "mods"))
            os.makedirs(os.path.join(path, "config"))
            os.makedirs(os.path.join(path, "saves"))
            os.makedirs(os.path.join(path, "resourcepacks"))
            os.makedirs(os.path.join(path, "shaderpacks"))
            
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
            
            return True, f"✔ Instancia '{safe_name}' creada", path
            
        except Exception as e:
            return False, f"❌ Error: {e}", None
    
    def install_mod(self, instance_name: str, url: str, filename: str) -> tuple:
        """
        Downloads and installs a mod file.
        
        Returns: (success: bool, message: str)
        """
        import requests
        
        # Find instance folder
        instances = self.get_instances()
        instance = next((inst for inst in instances if inst['name'] == instance_name), None)
        
        if not instance:
            return False, f"❌ Instancia '{instance_name}' no encontrada"
        
        mods_path = os.path.join(instance['path'], "mods")
        
        if not os.path.exists(mods_path):
            os.makedirs(mods_path)
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            file_path = os.path.join(mods_path, filename)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True, f"✔ Mod '{filename}' instalado"
            
        except Exception as e:
            return False, f"❌ Error descargando: {e}"
