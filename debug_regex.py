import re
import sys

def test_regex():
    print("=== DEBUG REGEX TEST ===")
    query = "Clona el perfil 1.21.5_Fabric a la 1.21.6"
    print(f"Query simulada: '{query}'")
    
    # The regex from main.py
    pattern = r'(\d+\.\d+(?:\.\d+)?[a-zA-Z0-9_]*)'
    print(f"Patrón Regex: {pattern}")
    
    matches = re.findall(pattern, query)
    print(f"Matches encontrados (Raw): {matches}")
    
    # Filter logic from limiting to ones with dots
    matches = [m for m in matches if "." in m]
    print(f"Matches filtrados (Con punto): {matches}")
    
    if len(matches) >= 2:
        print("✅ ÉXITO: Se detectaron suficientes versiones para migrar.")
        print(f"Origen: {matches[0]}")
        print(f"Destino: {matches[1]}")
    else:
        print("❌ FALLO: No se encontraron 2 versiones.")

if __name__ == "__main__":
    test_regex()
