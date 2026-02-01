"""
MineGenesis V6.0 - LLM Brain
Separate tool sets for client instances vs. dedicated servers.
"""
from src.ai.llm_client import get_client
import json

SYSTEM_PROMPT = """
Eres MineGenesis V6.0, un asistente que maneja DOS sistemas separados:
1. CLIENT INSTANCES (Perfiles de cliente para JUGAR)
2. DEDICATED SERVERS (Servidores dedicados para HOSTEAR)

CONTEXTO ACTUAL:
Client Instances: {client_list}
Dedicated Servers: {server_list}
{additional_context}

HERRAMIENTAS PARA CLIENTES (Jugar):
- "create_client_profile": {{"name": str, "version": str, "loader": str}}
  → Crea un perfil de CLIENTE vacío. ÚSALO SOLO si el usuario NO pide mods.

- "plan_instance": {{"name": str, "version": str, "loader": str, "mods": [str]}}
  → [IMPORTANTE] ÚSALO SIEMPRE QUE EL USUARIO PIDA UNA INSTANCIA CON MODS.
  → Esta herramienta busca los mods, resuelve dependencias, muestra una tabla al usuario y crea todo en un solo paso inteligente.
  → mods: Lista de nombres aproximados (ej: ["sodium", "iris", "litematica"])
  
- "select_client": {{"name": str}}
  → Selecciona una instancia de cliente como activa
  
- "search_mod": {{"query": str}}
  → Busca mods para instalar en un cliente (solo busca)

- "list_mods": {{"instance_name": str}}
  → Devuelve la lista de archivos .jar instalados en un perfil de cliente.
  → ÚSALO para saber qué mods tiene un cliente antes de migrarlo o actualizarlo.

- "install_mod": {{"instance_name": str, "url": str, "filename": str, "mod_id": str}}
  → Instala un mod en un perfil de CLIENTE.

- "migrate_profile": {{"source_name": str, "new_name": str, "target_version": str}}
  → ÚSALO cuando el usuario quiera actualizar, clonar o migrar un perfil a una NUEVA VERSIÓN manteniendo sus mods.
  → Esta herramienta identifica los mods del origen, busca versiones compatibles e instala todo automáticamente.

HERRAMIENTAS PARA SERVIDORES (Hostear):
- "create_dedicated_server": {{"name": str, "version": str, "server_type": str}}
  → Crea un servidor DEDICADO completo con:
    * Descarga automática del server.jar
    * Aceptación de EULA
    * Scripts de inicio (start.bat/start.sh)
  → server_type debe ser: "vanilla", "paper", o "fabric"
  
- "select_server": {{"name": str}}
  → Selecciona un servidor como activa
  
- "search_plugin": {{"query": str}}
  → Busca plugins/mods para servidores. PROPORCIONA EL "slug" o "project_id" para instalar.

- "install_plugin": {{"server_name": str, "url": str, "filename": str, "mod_id": str}}
  → Instala un plugin/mod en el servidor
  → "mod_id" DEBE ser el slug de Modrinth (ej: "create", "sodium") para verificar compatibilidad.
  → Si no sabes el "mod_id", usa primero "search_plugin".

HERRAMIENTAS GENERALES:
- "list_all": {{}}
  → Muestra el dashboard visual con ambas tablas (clientes y servidores).
  → USA ESTA HERRAMIENTA si el usuario pide "ver qué tengo", "listar", "status", etc.
  → NO listes los items en texto. DEJA QUE LA UI LO HAGA.

- "none": {{}}
  → Solo respuesta conversacional

RESPUESTA OBLIGATORIA (JSON):
{{
  "thought": "Análisis breve",
  "tool": "nombre_herramienta",
  "params": {{"key": "value"}},
  "response_text": "Mensaje para el usuario"
}}

REGLAS CRÍTICAS:
1. NUNCA inventes nombres - solo usa los de las listas anteriores.
2. NUNCA inventes versiones - se validarán contra Mojang API.
3. Para mods/plugins, SOLO búscalos, NO los instales directamente, EXCEPTO si el usuario pide explícitamente una instalación o MIGRACIÓN.
4. MIGRACIÓN: Si el usuario pide crear una versión nueva con mods de otra, utiliza SIEMPRE "migrate_profile".
5. JSON: Responde ÚNICAMENTE con el objeto JSON. No añadas texto fuera.

EJEMPLOS:
Usuario: "clona el perfil 1.21.5 a la 1.21.6"
{{
  "thought": "Usaré la herramienta de migración inteligente para mover los mods automáticamente",
  "tool": "migrate_profile",
  "params": {{"source_name": "1.21.5_Fabric", "new_name": "1.21.6_Migrated", "target_version": "1.21.6"}},
  "response_text": "Iniciando migración inteligente a la 1.21.6..."
}}

Usuario: "crea un servidor pvp 1.21"
{{
  "thought": "Usuario quiere un servidor dedicado para hostear PvP",
  "tool": "create_dedicated_server",
  "params": {{"name": "PvP_Server", "version": "1.21", "server_type": "paper"}},
  "response_text": "Creando servidor dedicado PvP con Paper 1.21..."
}}
"""

class LLMBrain:
    def __init__(self):
        self.client = None
        self.model = None
        self.provider = None
        self.history = [] # Turn history

    def configure(self, provider: str, api_key: str, model: str = None):
        """Re-configures the LLM client dynamically."""
        self.provider = provider
        self.model = model if model else "llama-3.3-70b-versatile"
        self.client = get_client(provider, api_key)
        self.history = [] # Reset history on reconfig
            
    def validate(self) -> bool:
        """Test if the current configuration works."""
        if not self.client:
            return False
        try:
            # Simple test query
            self.client.send("You are a test bot", "ping")
            return True
        except Exception:
            return False

    def clear_history(self):
        self.history = []

    def query(self, user_input: str, clients: list, servers: list, current_client: str = None, current_server: str = None) -> str:
        """
        Sends query with real client and server data and maintains history for the current session.
        """
        # Format lists for prompt
        client_str = ", ".join([f"'{c['name']}'" for c in clients]) if clients else "Ninguno"
        server_str = ", ".join([f"'{s['name']}'" for s in servers]) if servers else "Ninguno"
        
        # Additional context
        additional = ""
        if current_client:
            cli = next((c for c in clients if c['name'] == current_client), None)
            if cli: additional += f"\nCliente activo: {current_client} (v{cli.get('version', '?')})"
        
        if current_server:
            srv = next((s for s in servers if s['name'] == current_server), None)
            if srv: additional += f"\nServidor activo: {current_server} (v{srv.get('version', '?')})"
        
        # Format system prompt
        system_prompt = SYSTEM_PROMPT.format(
            client_list=client_str,
            server_list=server_str,
            additional_context=additional
        )
        
        try:
            # Build messages list
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add previous history
            messages.extend(self.history)
            
            # Add latest user message WITH JSON ENFORCEMENT
            final_prompt = f"{user_input}\n\n(IMPORTANT: Responda ÚNICAMENTE con el bloque JSON. Sin texto conversacional antes ni después.)"
            messages.append({"role": "user", "content": final_prompt})
            
            # Send to client
            response = self.client.send_messages(messages)
            
            # Save interaction to history
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": response})
            
            # Limit history
            if len(self.history) > 20:
                self.history = self.history[-20:]
            
            return response
            
        except Exception as e:
            return f'{{"response_text": "Error LLM: {e}", "tool": "none", "params": {{}}}}'
