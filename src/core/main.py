"""
MineGenesis V17.0 - PARANOID DEBUG MODE
Este archivo fuerza la migración si detecta la intención, ignorando los errores de la IA.
"""
print("\n\n!!! MODO DEBUG ACTIVADO - SI FALLA, TE DIRÉ POR QUÉ !!!\n\n")
import os
import sys
import json
import re
from src.core.settings import Settings
from src.managers.instance_manager import InstanceManager
from src.managers.server_manager import ServerManager
from src.managers.migration_manager import MigrationManager
from src.ai.llm_brain import LLMBrain
from src.api.minecraft_api import validator
import src.core.ui as ui


# --- CONFIGURACIÓN DE UI DE EMERGENCIA ---
# Definimos esto aquí por si tu ui.py no se actualizó, para evitar crash
def fallback_migration_report(report):
    ui.console.print("\n[bold yellow]REPORTE DE MIGRACIÓN (MODO TEXTO):[/bold yellow]")
    if report.get("error"):
        ui.console.print(f"[red]❌ ERROR: {report['error']}[/red]")

    success_count = len(report.get('success', []))
    fail_count = len(report.get('failed', []))

    ui.console.print(f"[green]✅ Éxitos: {success_count}[/green]")
    ui.console.print(f"[red]❌ Fallos: {fail_count}[/red]")

    if success_count > 0:
        ui.console.print("[dim]Mods instalados:[/dim]")
        for s in report['success']:
            ui.console.print(f"  - {s.get('name', '?')}")


def main():
    # 1. INICIO RÁPIDO
    # Verificación simple de onboarding
    if not os.path.exists("config/.env") and not os.path.exists("config/settings.json"):
        import src.core.setup_wizard as setup_wizard
        setup_wizard.run_onboarding()

    settings = Settings()
    active_provider = settings.get_active_provider()

    # Init Managers
    instances_path_val = settings.get_instances_path()
    im = InstanceManager(instances_path_val)
    sm = ServerManager(settings.get_servers_path())
    mm = MigrationManager(im, root_path=instances_path_val)
    brain = LLMBrain()

    # Configurar IA
    p_conf = settings.get_provider_config(active_provider)
    brain.configure(active_provider, p_conf.get("api_key"), p_conf.get("model"))

    # Render Inicial
    os.system('cls' if os.name == 'nt' else 'clear')
    ui.print_banner(model_name=active_provider.upper(), profile="DEBUG MODE")
    ui.render_dashboard(im.get_instances(), sm.get_servers())

    current_instance = settings.get_last_instance()
    current_server = settings.get_last_server()

    while True:
        try:
            # Contexto visual
            prompt_label = f"[CLIENT:{current_instance}]" if current_instance else "[GLOBAL]"
            ui.console.print()
            user_input = ui.ask_user(f"[bold red]DEBUG[/bold red] {prompt_label} > ")

            if not user_input.strip(): continue

            # Comandos rápidos
            if user_input.lower() in ["exit", "salir"]: sys.exit(0)

            # --- 1. CONSULTA A LA IA ---
            ui.console.print("[dim]🧠 Consultando al cerebro...[/dim]", end="\r")
            try:
                response = brain.query(user_input, im.get_instances(), sm.get_servers(), current_instance,
                                       current_server)
            except Exception as e:
                ui.console.print(f"[red]Error conectando con la IA: {e}[/red]")
                continue

            # --- 2. EXTRACCIÓN DE JSON (DEBUG) ---
            # Limpieza brutal del JSON
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            try:
                # Regex para encontrar el primer objeto JSON válido { ... }
                match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if match:
                    json_str = match.group(0)
                data = json.loads(json_str)
            except:
                ui.console.print(f"[dim red]La IA no devolvió JSON válido. Respuesta raw: {response[:50]}...[/dim red]")
                data = {}

            tool = data.get("tool")
            params = data.get("params", {})

            # Si hay texto de respuesta, muéstralo
            if data.get("response_text"):
                ui.print_ai_response(data["response_text"])

            ui.console.print(f"[bold cyan]🔧 TOOL DETECTADA POR IA:[/bold cyan] '{tool}'")

            # --- 3. OVERRIDE (LA FUERZA BRUTA) ---
            # Si el usuario dice "clona" y la IA falla, tomamos el control MANUALMENTE.
            is_migration_intent = any(k in user_input.lower() for k in ["clona", "migra", "copia"])

            if is_migration_intent and (not tool or tool == "none" or tool == "list_mods"):
                ui.console.print("[bold magenta]⚡ DETECTADA INTENCIÓN DE MIGRACIÓN - ACTIVANDO OVERRIDE[/bold magenta]")
                tool = "migrate_profile"

                # Regex para sacar versiones/nombres del input del usuario
                # Busca patrones como "1.21.6", "MyProfile", etc.
                parts = user_input.split()
                versions = re.findall(r'(\d+\.\d+(?:\.\d+)?)', user_input)

                # Intentamos deducir origen y destino
                src = params.get(
                    "source_name") or current_instance or "1.21.5_Fabric"  # Fallback hardcoded si todo falla
                tgt = params.get("target_version")

                if versions:
                    tgt = versions[-1]  # Asumimos la última versión mencionada es el destino

                if not tgt: tgt = "1.21.6"  # Último recurso

                params = {
                    "source_name": src,
                    "new_name": f"Migrated_to_{tgt}",
                    "target_version": tgt
                }
                ui.console.print(f"[dim]Parámetros forzados: {params}[/dim]")

            # --- 4. EJECUCIÓN DE TOOLS ---
            if not tool or tool == "none":
                continue

            # >>> BLOQUE DE MIGRACIÓN BLINDADO <<<
            if tool == "migrate_profile":
                src = params.get("source_name") or params.get("instance_name") or params.get("name")
                tgt = params.get("target_version") or params.get("version")
                new_n = params.get("new_name") or f"Migrated_{tgt}"

                if not src or not tgt:
                    ui.print_error(f"Faltan parámetros: Src={src}, Tgt={tgt}")
                else:
                    ui.console.print(f"[bold green]🚀 EJECUTANDO MIGRACIÓN REAL: {src} -> {tgt}[/bold green]")

                    try:
                        # LLAMADA AL BACKEND
                        result = mm.migrate_profile(src, new_n, tgt)

                        # DEBUG DEL RESULTADO
                        if not result:
                            ui.console.print("[bold red]❌ EL BACKEND DEVOLVIÓ NONE/VACÍO[/bold red]")
                        else:
                            # ui.console.print(f"[dim]Resultado: {result}[/dim]") # Descomentar si quieres ver el raw

                            # INTENTO DE RENDERIZADO UI
                            if hasattr(ui, 'print_migration_report'):
                                ui.print_migration_report(result)
                            else:
                                fallback_migration_report(result)

                            # Refrescar tabla
                            ui.render_dashboard(im.get_instances(), sm.get_servers())

                    except Exception as e:
                        ui.console.print(f"[bold red]❌ CRASH EN PYTHON:[/bold red] {e}")
                        import traceback
                        traceback.print_exc()

            # --- OTRAS HERRAMIENTAS ---
            elif tool == "list_all":
                ui.render_dashboard(im.get_instances(), sm.get_servers())

            elif tool == "create_client_profile":
                name = params.get("name", "New_Profile")
                ver = params.get("version", "1.21.1")
                ldr = params.get("loader", "fabric")
                with ui.show_spinner("Creando perfil...") as p:
                    ok, msg, _ = im.create_instance(name, ver, ldr)
                if ok:
                    ui.print_success(msg)
                else:
                    ui.print_error(msg)
                ui.render_dashboard(im.get_instances(), sm.get_servers())

            elif tool == "install_mod":
                # Lógica existente...
                pass

            # Feedback loop
            ui.print_separator()

        except KeyboardInterrupt:
            break
        except Exception as e:
            ui.console.print(f"[bold red]❌ ERROR FATAL EN MAIN LOOP: {e}[/bold red]")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()