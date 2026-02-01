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
            
            return True, f"Instancia '{safe_name}' creada para Minecraft {version} ({loader})", safe_name
            
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

    # --- V23.0 INTELLIGENT MOD PLANNER ---

    def search_modrinth(self, query: str, version: str, loader: str) -> Optional[Dict]:
        """Deep search on Modrinth for a specific version/loader."""
        import requests
        base = "https://api.modrinth.com/v2"
        
        # 1. Search Project
        try:
            # Facets: ver is version, categories is loader
            facets = f'[["versions:{version}"], ["categories:{loader}"]]'
            r = requests.get(f"{base}/search", params={"query": query, "facets": facets}, timeout=5)
            if r.status_code != 200: return None
            hits = r.json().get("hits", [])
            if not hits: return None
            
            project = hits[0] # Best match
            pid = project["project_id"]
            
            # 2. Get Version File (STRICT)
            # We strictly request the version, but we also verify the result.
            params = {
                "loaders": f'["{loader}"]', 
                "game_versions": f'["{version}"]'
            }
            r_ver = requests.get(f"{base}/project/{pid}/version", params=params, timeout=5)
            versions = r_ver.json()
            
            if not versions: 
                # Retry without explicit version param to check if we can find a loose match, 
                # BUT manually filter results to be safe.
                # (Some mods tag '1.21' instead of '1.21.6')
                return None
            
            # Strict Filter: Ensure the returned file actually supports the specific version requested
            target_ver = None
            for v in versions:
                if version in v.get("game_versions", []):
                    target_ver = v
                    break
            
            if not target_ver:
                 return None

            primary_file = next((f for f in target_ver['files'] if f['primary']), target_ver['files'][0])
            
            return {
                "name": project["title"],
                "project_id": pid,
                "version_id": target_ver["id"],
                "filename": primary_file["filename"],
                "url": primary_file["url"],
                "dependencies": target_ver.get("dependencies", [])
            }
        except Exception as e:
            print(f"Debug Search Error: {e}")
            return None

    def resolve_mod_setup(self, mod_names: List[str], version: str, loader: str) -> Dict:
        """
        Generates a complete installation plan with dependencies.
        Returns: { 'found': [], 'missing': [], 'dependencies': [] }
        """
        plan = {
            "target": {"version": version, "loader": loader},
            "mods": [], # Requested mods found
            "dependencies": [], # Auto-resolved deps
            "missing": []
        }
        
        resolved_ids = set()
        
        # Helper for recursive dependency resolution
        def resolve_dep(dep_pid):
            if dep_pid in resolved_ids: return
            resolved_ids.add(dep_pid)
            
            # Fetch dep info (simplified search by ID) (This is tricky without name, need to get project by ID)
            import requests
            try:
                # Get Project Metadata to get Name
                r_proj = requests.get(f"https://api.modrinth.com/v2/project/{dep_pid}", timeout=5)
                if r_proj.status_code != 200: return
                p_data = r_proj.json()
                slug = p_data["slug"]
                
                # Re-use search logic using slug which is safer for version matching
                mod_data = self.search_modrinth(slug, version, loader)
                if mod_data:
                    mod_data["type"] = "Dependency"
                    plan["dependencies"].append(mod_data)
                    # Recurse? Maybe too deep nicely, but let's do 1 level? 
                    # For safety avoids infinite loops. Most critical deps are 1 level deep (Fabric API, MaLiLib).
            except: pass

        for name in mod_names:
            mod_data = self.search_modrinth(name, version, loader)
            if mod_data:
                mod_data["type"] = "Requested"
                plan["mods"].append(mod_data)
                resolved_ids.add(mod_data["project_id"])
                
                # Check Dependencies
                for dep in mod_data["dependencies"]:
                    # type: "required" or "optional"
                    if dep.get("dependency_type") == "required":
                        pid = dep.get("project_id") or dep.get("version_id") # Note: Modrinth deps can be tricky
                        # Usually project_id is what we want
                        if dep.get("project_id"):
                            resolve_dep(dep["project_id"])
            else:
                plan["missing"].append(name)
                
        return plan
