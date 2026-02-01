import abc
import os
from config_manager import ConfigManager
from groq import Groq
from google import genai
from openai import OpenAI
from anthropic import Anthropic

# STATE: GLOBAL
PROMPT_global = """
Eres MineGenesis (Menú Principal).
El usuario está gestionando sus instancias.

CAPACIDADES (Responde JSON):
- {{"action": "CREATE_INSTANCE", "name": "Nombre", "version": "1.20", "loader": "fabric"}}
- {{"action": "DELETE_INSTANCE", "name": "Nombre"}}
- {{"action": "SELECT_INSTANCE", "name": "Nombre"}}

CONTEXTO:
{context}

Si el usuario quiere instalar un mod, dile que primero debe SELECCIONAR una instancia.
"""

# STATE: INSTANCE
PROMPT_instance = """
Eres MineGenesis (Gestor de Instancia: {inst_name}).
Versión: {inst_ver} | Loader: {inst_loader}

CAPACIDADES (Responde JSON):
- {{"action": "SEARCH_MOD", "query": "nombre"}}
- {{"action": "BUILD_SERVER"}} -> Convierte esta instancia en un servidor desplegable.
- {{"action": "EXIT_TO_MENU"}} -> Vuelve al menú global.

CONTEXTO:
{context}

REGLAS:
- Al instalar mods, asume compatibilidad con {inst_ver}.
- Recuerda que 'build_server' filtra mods de cliente automáticamente.
"""

def get_client(model_name: str, api_key: str):
    if not api_key: return None 
    model_name = model_name.lower()
    if "groq" in model_name: return GroqClient(api_key)
    if "gemini" in model_name: return GeminiClient(api_key)
    if "openai" in model_name: return OpenAIClient(api_key)
    if "anthropic" in model_name: return AnthropicClient(api_key)
    return GroqClient(api_key)

class LLMClient(abc.ABC):
    @abc.abstractmethod
    def send(self, system: str, user: str) -> str: pass

class GroqClient(LLMClient):
    def __init__(self, key): 
        self.c = Groq(api_key=key)
        self.m = "llama-3.3-70b-versatile"
    def send(self, s, u):
        try:
            return self.c.chat.completions.create(
                messages=[{"role":"system","content":s},{"role":"user","content":u}],
                model=self.m
            ).choices[0].message.content
        except Exception as e: return f"Error Groq: {e}"

class GeminiClient(LLMClient):
    def __init__(self, key): 
        self.c = genai.Client(api_key=key)
        self.m = "gemini-2.0-flash"
    def send(self, s, u):
        try:
            return self.c.models.generate_content(
                model=self.m, contents=f"{s}\n\nUSER: {u}"
            ).text
        except Exception as e: return f"Error Gemini: {e}"

class OpenAIClient(LLMClient):
    def __init__(self, key):
        self.c = OpenAI(api_key=key)
        self.m = "gpt-4o"
    def send(self, s, u):
        try:
            return self.c.chat.completions.create(
                model=self.m, messages=[{"role":"system","content":s},{"role":"user","content":u}]
            ).choices[0].message.content
        except Exception as e: return f"Error OpenAI: {e}"

class AnthropicClient(LLMClient):
    def __init__(self, key):
        self.c = Anthropic(api_key=key)
        self.m = "claude-3-opus-20240229"
    def send(self, s, u):
        try:
            return self.c.messages.create(
                model=self.m, max_tokens=1024, system=s,
                messages=[{"role":"user","content":u}]
            ).content[0].text
        except Exception as e: return f"Error Claude: {e}"
