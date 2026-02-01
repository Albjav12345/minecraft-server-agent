"""
MineGenesis V4.0 - Minecraft API Validator
The Source of Truth - validates ALL versions against real Mojang/Modrinth APIs.
"""
import requests
from typing import Tuple, List, Dict, Optional

class MinecraftValidator:
    def __init__(self):
        self.version_cache = None
        self.mojang_manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
        self.modrinth_versions_url = "https://api.modrinth.com/v2/tag/game_version"
    
    def get_all_versions(self) -> List[str]:
        """
        Fetches ALL Minecraft versions from Mojang.
        Returns list of version strings (e.g., ["1.20.4", "1.20.3", ...])
        """
        if self.version_cache:
            return self.version_cache
        
        try:
            response = requests.get(self.mojang_manifest_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract release versions only
            versions = [
                v["id"] for v in data["versions"] 
                if v["type"] == "release"
            ]
            
            self.version_cache = versions
            return versions
            
        except Exception as e:
            print(f"Warning: Mojang API failed ({e}), using fallback")
            # Fallback to known stable versions
            return ["1.21.4", "1.21.3", "1.21.1", "1.20.6", "1.20.4", "1.20.1", "1.19.4", "1.19.2", "1.18.2", "1.16.5"]
    
    def validate_version(self, version: str) -> Tuple[bool, str]:
        """
        Validates if a Minecraft version actually exists.
        
        Returns:
            (True, "") if valid
            (False, "error message with suggestions") if invalid
        """
        valid_versions = self.get_all_versions()
        
        if version in valid_versions:
            return True, ""
        
        # Find similar versions to suggest
        base = version.split('.')[0] + '.' + version.split('.')[1] if '.' in version else version
        similar = [v for v in valid_versions if v.startswith(base)][:5]
        
        if similar:
            msg = f"❌ La versión '{version}' no existe.\n💡 Versiones similares: {', '.join(similar)}"
        else:
            latest = valid_versions[:5]
            msg = f"❌ La versión '{version}' no existe.\n💡 Últimas estables: {', '.join(latest)}"
        
        return False, msg
    
    def get_loader_info(self, mc_version: str, loader: str) -> Tuple[bool, str]:
        """
        Validates if a loader (fabric/forge/paper) exists for the MC version.
        
        For now, we'll assume fabric/paper are generally available.
        Real implementation would check fabric-meta API / PaperMC API.
        """
        if loader.lower() not in ["fabric", "paper", "forge", "quilt"]:
            return False, f"Loader '{loader}' desconocido. Usa: fabric, paper, forge, quilt"
        
        # Simplified validation - in production, check actual loader APIs
        return True, ""
    
    def search_mod(self, query: str, mc_version: str, loader: str = "fabric") -> List[Dict]:
        """
        Searches Modrinth for mods compatible with the exact MC version.
        
        Returns list of mod dictionaries with: title, slug, author, description
        """
        try:
            facets = f'[["project_type:mod"],["versions:{mc_version}"],["categories:{loader}"]]'
            
            response = requests.get(
                "https://api.modrinth.com/v2/search",
                params={"query": query, "facets": facets, "limit": 10},
                timeout=10
            )
            response.raise_for_status()
            
            hits = response.json().get("hits", [])
            return [
                {
                    "title": h["title"],
                    "slug": h["slug"],
                    "author": h["author"],
                    "description": h["description"][:100] + "..."
                }
                for h in hits
            ]
            
        except Exception as e:
            print(f"Modrinth search failed: {e}")
            return []
    
    def get_mod_download(self, slug: str, mc_version: str, loader: str) -> Optional[Dict]:
        """
        Gets download URL for a specific mod version.
        
        Returns: {"url": str, "filename": str, "version": str} or None
        """
        try:
            # Get project info
            project = requests.get(f"https://api.modrinth.com/v2/project/{slug}", timeout=10).json()
            project_id = project["id"]
            
            # Get versions
            versions_data = requests.get(
                f"https://api.modrinth.com/v2/project/{project_id}/version",
                params={"game_versions": f'["{mc_version}"]', "loaders": f'["{loader}"]'},
                timeout=10
            ).json()
            
            if not versions_data:
                return None
            
            # Get primary file from latest version
            latest = versions_data[0]
            primary_file = latest["files"][0]
            
            return {
                "url": primary_file["url"],
                "filename": primary_file["filename"],
                "version": latest["version_number"]
            }
            
        except Exception as e:
            print(f"Download fetch failed: {e}")
            return None

# NEW V6.0: Server JAR Download Functions
def get_server_jar_url(version: str, server_type: str) -> Optional[str]:
    """
    Gets download URL for server JAR files.
    
    Args:
        version: Minecraft version (e.g., "1.21")
        server_type: 'vanilla', 'paper', or 'fabric'
    
    Returns:
        Download URL string or None
    """
    try:
        if server_type.lower() == "vanilla":
            return _get_vanilla_server_url(version)
        elif server_type.lower() == "paper":
            return _get_paper_server_url(version)
        elif server_type.lower() == "fabric":
            return _get_fabric_server_url(version)
        else:
            return None
    except Exception as e:
        print(f"Error getting server JAR URL: {e}")
        return None

def _get_vanilla_server_url(version: str) -> Optional[str]:
    """Gets Mojang vanilla server.jar URL."""
    try:
        # Get version manifest
        manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
        manifest = requests.get(manifest_url, timeout=10).json()
        
        # Find version
        version_data = next((v for v in manifest["versions"] if v["id"] == version), None)
        if not version_data:
            return None
        
        # Get version JSON
        version_json = requests.get(version_data["url"], timeout=10).json()
        
        # Extract server download URL
        return version_json["downloads"]["server"]["url"]
        
    except Exception as e:
        print(f"Vanilla server URL fetch failed: {e}")
        return None

def _get_paper_server_url(version: str) -> Optional[str]:
    """Gets PaperMC server JAR URL."""
    try:
        # Get builds for version
        builds_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
        builds = requests.get(builds_url, timeout=10).json()
        
        if "builds" not in builds:
            return None
        
        # Get latest build
        latest_build = builds["builds"][-1]["build"]
        
        # Construct download URL
        jar_name = f"paper-{version}-{latest_build}.jar"
        return f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/{jar_name}"
        
    except Exception as e:
        print(f"Paper server URL fetch failed: {e}")
        return None

def _get_fabric_server_url(version: str) -> Optional[str]:
    """Gets Fabric server launcher URL."""
    try:
        # Get loader versions
        loader_url = "https://meta.fabricmc.net/v2/versions/loader"
        loaders = requests.get(loader_url, timeout=10).json()
        
        if not loaders:
            return None
        
        latest_loader = loaders[0]["version"]
        
        # Get installer version
        installer_url = "https://meta.fabricmc.net/v2/versions/installer"
        installers = requests.get(installer_url, timeout=10).json()
        
        if not installers:
            return None
        
        latest_installer = installers[0]["version"]
        
        # Construct server launcher URL
        return f"https://meta.fabricmc.net/v2/versions/loader/{version}/{latest_loader}/{latest_installer}/server/jar"
        
    except Exception as e:
        print(f"Fabric server URL fetch failed: {e}")
        return None

# Global singleton
validator = MinecraftValidator()
