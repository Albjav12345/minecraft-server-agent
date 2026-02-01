"""
MineGenesis V4.0 - LLM Interface
Enforces strict JSON responses with dynamic context injection.
"""
from groq import Groq
from config_manager import ConfigManager

# SYSTEM PROMPT with dynamic variables
SYSTEM_PROMPT_TEMPLATE = """
Eres MineGenesis V4.0, un asistente especializado en gestión de instancias de Minecraft.

CONTEXTO DEL SISTEMA (DATOS REALES):
Instancias detectadas en disco: {instance_list}
{additional_context}

REGLAS CRÍTICAS (ZERO-HALLUCINATION):
1. NUNCA inventes nombres de instancias. Solo usa los nombres EXACTOS de la lista anterior.
2. NUNCA inventes versiones de Minecraft. El sistema validará todas las versiones contra la API de Mojang.
3. Tu respuesta DEBE ser un JSON válido con esta estructura EXACTA:

{{
  "thought": "Análisis breve de lo que el usuario quiere",
  "tool": "nombre_de_la_herramienta",
  "params": {{"param1": "valor1", "param2": "valor2"}},
  "response_text": "Mensaje amigable para el usuario"
}}

HERRAMIENTAS DISPONIBLES:
- "create_instance": params: {{"name": str, "version": str, "loader": str}}
- "select_instance": params: {{"name": str}} (debe existir en la lista)
- "list_instances": params: {{}}
- "search_mod": params: {{"query": str, "instance_name": str}}
- "install_mod": params: {{"slug": str, "instance_name": str}}
- "get_details": params: {{"name": str}}

EJEMPLO DE RESPUESTA CORRECTA:
{{
  "thought": "El usuario quiere crear una instancia para 1.20.4",
  "tool": "create_instance",
  "params": {{"name": "Survival_1.20", "version": "1.20.4", "loader": "fabric"}},
  "response_text": "Voy a crear una instancia de Minecraft 1.20.4 con Fabric llamada 'Survival_1.20'"
}}

PROHIBICIONES:
- NO respondas con texto plano fuera del JSON
- NO uses placeholders como "NombreDeLaInstancia" o "MiInstancia"
- NO inventes versiones como "1.21.11" (no existe)
"""

class LLMInterface:
    def __init__(self):
        cfg = ConfigManager()
        cfg.ensure_configured()
        api_key = cfg.get_api_key("groq")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def query(self, user_input: str, instance_list: list, additional_context: str = "") -> str:
        """
        Sends query to LLM with REAL instance data injected.
        
        Args:
            user_input: User's message
            instance_list: REAL list of instance names from disk
            additional_context: Extra info (e.g., current instance details)
        
        Returns:
            Raw LLM response (should be JSON)
        """
        # Format instance list nicely
        if instance_list:
            inst_str = ", ".join([f"'{name}'" for name in instance_list])
        else:
            inst_str = "Ninguna (carpeta vacía)"
        
        # Inject REAL data into system prompt
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            instance_list=inst_str,
            additional_context=additional_context
        )
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                model=self.model,
                temperature=0.2,  # Low temp for deterministic, structured output
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f'{{"response_text": "Error de conexión con LLM: {e}"}}'
