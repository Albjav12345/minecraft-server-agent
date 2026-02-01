"""
MineGenesis V7.0 - Mod Intelligence
Analyzes mod compatibility (Client vs Server) using Modrinth API.
Prevents installing client-only mods on servers and vice-versa.
"""
import requests
from typing import Dict, Tuple

class ModIntelligence:
    def __init__(self):
        self.api_url = "https://api.modrinth.com/v2"
        self.headers = {"User-Agent": "MineGenesis/7.0 (alberto@example.com)"}

    def analyze_mod_compatibility(self, mod_id_or_slug: str, target_type: str) -> Tuple[str, str]:
        """
        Analyzes a mod's compatibility with the target environment.
        
        Args:
           mod_id_or_slug: The Modrinth ID or slug of the mod.
           target_type: "client" or "server".
           
        Returns:
           Tuple (Action, Reason). 
           Action: "INSTALL", "WARN", "BLOCK"
        """
        try:
            # 1. Get Project Data
            resp = requests.get(f"{self.api_url}/project/{mod_id_or_slug}", headers=self.headers)
            if resp.status_code != 200:
                return "WARN", f"No pude analizar '{mod_id_or_slug}' en Modrinth (Error {resp.status_code}). Proceder con precaución."
            
            data = resp.json()
            client_side = data.get("client_side", "unknown")  # required, optional, unsupported
            server_side = data.get("server_side", "unknown")  # required, optional, unsupported
            
            # 2. Logic Matrix
            if target_type == "server":
                if server_side == "unsupported":
                    return "BLOCK", "Este mod es CLIENT-SIDE (Solo visual/jugar). No funcionará en el servidor."
                if server_side == "optional":
                    if client_side == "required":
                         return "WARN", "Se instalará, pero recuerda que LOS JUGADORES también necesitan tenerlo instalado."
                    return "INSTALL", "Compatible con servidor (Opcional)."
                if server_side == "required":
                    return "INSTALL", "Mod de servidor requerido."
                
                # If unknown but client requires it, warn
                if client_side == "required":
                    return "WARN", "Probablemente requiere que los clientes también lo tengan."
                    
                return "INSTALL", "Compatibilidad asumida."

            elif target_type == "client":
                if client_side == "unsupported":
                     return "BLOCK", "Este mod es SERVER-SIDE (Plugins/Optimizaciones de host). No sirve para el cliente."
                return "INSTALL", "Compatible con cliente."
                
            return "WARN", "Tipo de target desconocido."

        except Exception as e:
            return "WARN", f"Error de conexión con Mod Intelligence: {e}"

# Singleton instance
intelligence = ModIntelligence()
