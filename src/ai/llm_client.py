"""
LLM Client V4.0 - Anti-Hallucination Edition
Enforces use of REAL data in all responses.
"""
import abc
# from config_manager import ConfigManager
from groq import Groq
from google import genai
from openai import OpenAI
from anthropic import Anthropic

# CRITICAL: Double braces for literal JSON in prompts
SYSTEM_PROMPT_GLOBAL = """
Eres MineGenesis V4.0 (Menú Global).

CONTEXTO DEL SISTEMA:
{system_context}

REGLAS CRÍTICAS:
1. **NUNCA inventes nombres**: Si el contexto dice "Instancias: Survival, Creative", SOLO puedes usar esos nombres EXACTOS.
2. **NUNCA inventes versiones**: Solo usa versiones que el sistema te confirme como válidas.
3. **JSON puro**: Responde SOLO con JSON, nada más. Formato: {{"action": "...", "params": {{...}}}}

ACCIONES DISPONIBLES:
- {{"action": "CREATE_INSTANCE", "name": "NombreReal", "version": "1.20.4", "loader": "fabric"}}
- {{"action": "SELECT_INSTANCE", "name": "NombreExacto"}}
- {{"action": "LIST_INSTANCES"}}

PROHIBIDO usar placeholders como "MiInstancia", "NombreDeLaInstancia", etc.
Si el usuario no da un nombre, genera uno ORIGINAL (ej: "Instance_001") y úsalo.
"""

SYSTEM_PROMPT_INSTANCE = """
Eres MineGenesis V4.0 (Gestor de Instancia).

INSTANCIA ACTIVA:
Nombre: {instance_name}
Versión: {instance_version}
Loader: {instance_loader}

CONTEXTO:
{instance_context}

ACCIONES DISPONIBLES:
- {{"action": "SEARCH_MOD", "query": "sodium"}}
- {{"action": "INSTALL_MOD", "slug": "sodium", "query": "sodium"}}
- {{"action": "BUILD_SERVER", "server_name": "MiServidor"}}
- {{"action": "EXIT_TO_MENU"}}

REGLAS:
1. Al buscar mods, usa {instance_version} como filtro.
2. Nombres exactos: Usa "{instance_name}" si te refieres a esta instancia.
3. Solo JSON en la respuesta.
"""

def get_client(model_name: str, api_key: str):
    """Factory method for LLM clients."""
    if not api_key:
        return None
    
    model_name = model_name.lower()
    if "groq" in model_name:
        return GroqClient(api_key)
    elif "gemini" in model_name:
        return GeminiClient(api_key)
    elif "openai" in model_name or "gpt" in model_name:
        return OpenAIClient(api_key)
    elif "anthropic" in model_name or "claude" in model_name:
        return AnthropicClient(api_key)
    else:
        return GroqClient(api_key)

class LLMClient(abc.ABC):
    @abc.abstractmethod
    def send_messages(self, messages: list[dict]) -> str:
        """Sends a list of messages (role/content) to the LLM."""
        pass
        
    def send(self, system: str, user: str) -> str:
        """Compatibility method for single-turn queries."""
        return self.send_messages([
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ])

class GroqClient(LLMClient):
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def send_messages(self, messages: list[dict]) -> str:
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error Groq: {e}"

class GeminiClient(LLMClient):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash"
    
    def send_messages(self, messages: list[dict]) -> str:
        try:
            # Gemini multi-turn via generate_content (simplified for this wrapper)
            # contents list in Gemini API is: [{"role": "user", "parts": [{"text": "..."}]}, ...]
            contents = []
            system_instruction = None
            
            for m in messages:
                if m["role"] == "system":
                    system_instruction = m["content"]
                else:
                    role = "user" if m["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": m["content"]}]})
            
            generation_config = {"response_mime_type": "application/json"}
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generation_config,
                system_instruction=system_instruction
            )
            return response.text
        except Exception as e:
            return f"Error Gemini: {e}"

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
    
    def send_messages(self, messages: list[dict]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error OpenAI: {e}"

class AnthropicClient(LLMClient):
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def send_messages(self, messages: list[dict]) -> str:
        try:
            # Separate system prompt
            system = next((m["content"] for m in messages if m["role"] == "system"), None)
            
            # Anthropic roles are 'user' and 'assistant'
            user_msgs = []
            for m in messages:
                if m["role"] == "system": continue
                role = "assistant" if m["role"] in ["assistant", "model"] else "user"
                user_msgs.append({"role": role, "content": m["content"]})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system,
                messages=user_msgs
            )
            return response.content[0].text
        except Exception as e:
            return f"Error Claude: {e}"
