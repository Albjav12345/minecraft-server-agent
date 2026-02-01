import requests
import src.core.ui as ui

BASE_URL = "https://api.modrinth.com/v2"

def search_project(query: str, project_type: str = "mod"):
    """Search for mods, plugins, etc."""
    params = {
        "query": query,
        "facets": f'[["project_type:{project_type}"]]'
    }
    try:
        resp = requests.get(f"{BASE_URL}/search", params=params)
        resp.raise_for_status()
        return resp.json().get("hits", [])
    except Exception as e:
        ui.print_error_panel(f"Error buscando en Modrinth: {e}")
        return []

def get_compatible_version(slug: str, loaders: list[str], game_versions: list[str]):
    """Get the primary file compatible with loader and version."""
    try:
        resp = requests.get(f"{BASE_URL}/project/{slug}/version")
        resp.raise_for_status()
        versions = resp.json()
        
        for v in versions:
            if any(l in v["loaders"] for l in loaders) and any(gv in v["game_versions"] for gv in game_versions):
                return v
        return None
    except Exception as e:
        return None

def resolve_dependencies(version_id: str, resolved: dict = None) -> dict:
    """Recursively resolve dependencies."""
    if resolved is None:
        resolved = {}
        
    if version_id in resolved:
        return resolved
        
    try:
        resp = requests.get(f"{BASE_URL}/version/{version_id}")
        resp.raise_for_status()
        data = resp.json()
        
        resolved[version_id] = {
            "name": data["name"], # Note: this is version name, might want project name separately
            "project_id": data["project_id"],
            "files": data["files"],
            "dependencies": []
        }
        
        # Check dependencies
        for dep in data.get("dependencies", []):
            if dep["dependency_type"] == "required": # and dep["version_id"] or dep["project_id"]
                # Modrinth dependency structure can be complex. 
                # If specific version_id is provided, use it. 
                # If only project_id, we need to find compatible version again (complex).
                # For this simplified CLI, we will try to follow strict version links if present.
                dep_ver_id = dep.get("version_id")
                if dep_ver_id:
                     # Recursive call
                     resolve_dependencies(dep_ver_id, resolved)
                     resolved[version_id]["dependencies"].append(dep["project_id"])
        
        return resolved
    except Exception as e:
        ui.print_error_panel(f"Error resolviendo dependencias: {e}")
        return resolved

# Helper for resolving dependencies starting from a project slug
def get_install_plan(slug: str, loader: str, mc_version: str):
    ui.show_spinner(f"Analizando dependencias para {slug}...")
    
    # 1. Get Project ID and Info
    try:
        p_resp = requests.get(f"{BASE_URL}/project/{slug}")
        p_resp.raise_for_status()
        project_data = p_resp.json()
        project_title = project_data["title"]
    except:
        return None, "Project not found"

    # 2. Get Compatible Version
    version_data = get_compatible_version(slug, [loader], [mc_version])
    if not version_data:
        return None, f"No version found for {mc_version} / {loader}"

    # 3. Resolve Dependencies Recursive
    # This is a simplified resolver. A full resolver is complex.
    # We will fetch the version dependency tree.
    plan = []
    
    # We'll use a queue system or recursive function that builds a flat list of 'to_install'
    # For MVP, let's just inspect the direct dependencies of the target version and alert the user
    # A full recursive resolver is heavy for a single file snippet, but let's try a best effort.
    
    # Using a simple list ensuring uniqueness
    to_check = [version_data]
    checked_ids = set()
    install_list = []
    
    while to_check:
        current = to_check.pop(0)
        vid = current["id"]
        if vid in checked_ids:
            continue
        checked_ids.add(vid)
        
        # Get project info for this version to display name
        pid = current["project_id"]
        # We might need to fetch project name if not available
        
        file_info = current["files"][0] # Primary file
        install_list.append({
            "name": f"Project {pid} - {current['name']}", 
            "type": "Mod",
            "version": current["version_number"],
            "url": file_info["url"],
            "filename": file_info["filename"]
        })
        
        # Dependencies
        for dep in current.get("dependencies", []):
            if dep["dependency_type"] == "required":
                # Find the version for this dependency
                if dep.get("version_id"):
                     # Fetch that specific version
                     try:
                         d_resp = requests.get(f"{BASE_URL}/version/{dep['version_id']}")
                         if d_resp.status_code == 200:
                             to_check.append(d_resp.json())
                     except: pass
                elif dep.get("project_id"):
                    # Find compatible version for this project
                    # We assume same loader/mc_version as parent
                     # Need to convert project_id to slug or search by id? 
                     # search by version endpoint supports project_id too
                     # But we don't have slug here. Modrinth allows GET /project/{id}/version
                     try:
                         # We need to find the latest compatible version for this dependency project
                         # This is expensive (N+1 requests), but required.
                         dep_vers_resp = requests.get(f"{BASE_URL}/project/{dep['project_id']}/version")
                         if dep_vers_resp.status_code == 200:
                             all_vers = dep_vers_resp.json()
                             # Filter
                             valid_v = None
                             for v in all_vers:
                                 if any(l in v["loaders"] for l in [loader]) and any(gv in v["game_versions"] for gv in [mc_version]):
                                     valid_v = v
                                     break
                             if valid_v:
                                 to_check.append(valid_v)
                     except: pass

    return install_list, None
