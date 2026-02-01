"""
MineGenesis V18.0 - TOGGLE DEBUG SYSTEM
Comando !debug para alternar entre UI limpia y Logs técnicos.
"""
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

# UI de Emergencia para reportes
def fallback_migration_report(report):
    ui.console.print("\n[bold yellow]REPORTE DE MIGRACIÓN (TEXTO):[/bold yellow]")
    if report.get("error"): ui.console.print(f"[red]❌ ERROR: {report['error']}[/red]")
    ui.console.print(f"[green]✅ Éxitos: {len(report.get('success', []))}[/green]")
    ui.console.print(f"[red]❌ Fallos: {len(report.get('failed', []))}[/red]")

def main():
    # --- SETUP ---
    if not os.path.exists("config/.env") and not os.path.exists("config/settings.json"):
        import src.core.setup_wizard as setup_wizard
        setup_wizard.run_onboarding()

    settings = Settings()
    active_provider = settings.get_active_provider()
    
    # Init Managers
    # NOTA: Pasamos la ruta explícita al MigrationManager (Fix V17.2)
    instances_path = settings.get_instances_path()
    im = InstanceManager(instances_path)
    sm = ServerManager(settings.get_servers_path())
    mm = MigrationManager(im, root_path=instances_path) 
    brain = LLMBrain()
    
    # Configure AI
    p_conf = settings.get_provider_config(active_provider)
    brain.configure(active_provider, p_conf.get("api_key"), p_conf.get("model"))

    # UI Init
    os.system('cls' if os.name == 'nt' else 'clear')
    ui.print_banner(model_name=active_provider.upper(), profile="Ready")
    ui.render_dashboard(im.get_instances(), sm.get_servers())
    
    current_instance = settings.get_last_instance()
    current_server = settings.get_last_server()

    # ESTADO GLOBAL
    debug_mode = False 

    while True:
        try:
            # Prompt Dinámico
            ctx_label = f"[CLIENT:{current_instance}]" if current_instance else "[GLOBAL]"
            debug_tag = "[bold yellow][DEBUG][/bold yellow] " if debug_mode else ""
            
            ui.console.print() 
            user_input = ui.ask_user(f"{debug_tag}{ctx_label} > ")
            
            if not user_input.strip(): continue

            # --- COMANDOS INTERNOS ---
            if user_input.lower() == "!debug":
                debug_mode = not debug_mode
                status = "ACTIVADO (Verás logs técnicos)" if debug_mode else "DESACTIVADO (Modo Limpio)"
                color = "green" if debug_mode else "red"
                ui.console.print(f"[{color}]🐛 MODO DEBUG {status}[/{color}]")
                continue

            if user_input.lower() in ["exit", "salir"]: sys.exit(0)

            if user_input.lower() == "cls":
                os.system('cls' if os.name == 'nt' else 'clear')
                ui.print_banner(model_name=active_provider.upper())
                ui.render_dashboard(im.get_instances(), sm.get_servers())
                continue

            # --- 1. CEREBRO IA ---
            if debug_mode: ui.console.print("[dim]🧠 Consultando API...[/dim]")
            else: ui.console.print("[dim italic]Procesando...[/dim italic]", end="\r")

            try:
                response = brain.query(user_input, im.get_instances(), sm.get_servers(), current_instance, current_server)
                if not debug_mode: ui.console.print(" " * 20, end="\r") # Limpiar línea
            except Exception as e:
                ui.print_error(f"Error de conexión IA: {e}")
                continue
            
            # --- 2. PARSEO JSON ---
            if debug_mode: ui.console.print(f"[dim yellow]RAW:[/dim yellow] {response[:80]}...")

            # Limpieza robusta
            json_str = response.strip()
            if "```json" in json_str: json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str: json_str = json_str.split("```")[1].split("```")[0].strip()
            
            try:
                match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if match: json_str = match.group(0)
                data = json.loads(json_str)
            except:
                if debug_mode: ui.console.print(f"[red]JSON Roto: {response}[/red]")
                data = {}

            tool = data.get("tool")
            params = data.get("params", {})
            
            # Mostrar respuesta de texto si existe
            if data.get("response_text"):
                ui.print_ai_response(data["response_text"])

            if debug_mode: ui.console.print(f"[cyan]🔧 Tool Detectada: {tool}[/cyan]")

            # --- 3. OVERRIDE SYSTEM (Migración) ---
            # Este sistema corrige a la IA si falla al detectar intención de migrar
            is_migra = any(k in user_input.lower() for k in ["clona", "migra", "copia"])
            
            if is_migra and (not tool or tool == "none" or tool == "list_mods"):
                if debug_mode: ui.console.print("[magenta]⚡ Override: Forzando migración[/magenta]")
                tool = "migrate_profile"
                
                # Deducción de parámetros
                vers = re.findall(r'(\d+\.\d+(?:\.\d+)?)', user_input)
                src = params.get("source_name") or current_instance or "1.21.5_Fabric"
                tgt = vers[-1] if vers else "1.21.6"
                
                params = {
                    "source_name": src,
                    "new_name": f"Migrated_{tgt}",
                    "target_version": tgt
                }

            # --- 4. EJECUCIÓN DE TOOLS ---
            if not tool or tool == "none":
                continue

            if tool == "migrate_profile":
                src = params.get("source_name")
                tgt = params.get("target_version")
                new_n = params.get("new_name")

                if not src or not tgt:
                    ui.print_error("Faltan datos para migrar.")
                else:
                    # Spinner en modo normal, Log en debug
                    if not debug_mode:
                        with ui.show_spinner(f"🚀 Migrando {src} a {tgt}...") as p:
                            try:
                                result = mm.migrate_profile(src, new_n, tgt)
                            except Exception as e:
                                result = {"error": str(e)}
                    else:
                        ui.console.print(f"[bold green]🚀 Debug: Iniciando migración {src}->{tgt}[/bold green]")
                        try:
                            result = mm.migrate_profile(src, new_n, tgt)
                            ui.console.print(f"[dim]Keys: {list(result.keys())}[/dim]")
                        except Exception as e:
                            ui.console.print(f"[bold red]CRASH: {e}[/bold red]")
                            result = None

                    # Renderizado
                    if result:
                        if hasattr(ui, 'print_migration_report'):
                            ui.print_migration_report(result)
                        else:
                            fallback_migration_report(result)
                        
                        ui.render_dashboard(im.get_instances(), sm.get_servers())
                    else:
                        ui.print_error("La migración falló (Sin resultado).")

            elif tool == "list_all":
                ui.render_dashboard(im.get_instances(), sm.get_servers())

            elif tool == "create_client_profile":
                name = params.get("name", "NewInstance")
                ver = params.get("version", "1.21.1")
                ldr = params.get("loader", "fabric")
                
                msg_spin = f"Creando perfil {name}..."
                if debug_mode: ui.console.print(f"[cyan]Creando: {name} ({ver})[/cyan]")
                
                # Ejecución (con o sin spinner según modo)
                if not debug_mode:
                    with ui.show_spinner(msg_spin):
                        ok, msg, _ = im.create_instance(name, ver, ldr)
                else:
                    ok, msg, _ = im.create_instance(name, ver, ldr)
                
                if ok: ui.print_success(msg)
                else: ui.print_error(msg)
                ui.render_dashboard(im.get_instances(), sm.get_servers())

            elif tool == "install_mod":
                # Lógica simplificada de ejemplo
                url = params.get("url")
                file = params.get("filename")
                tgt = params.get("instance_name") or current_instance
                if url and file:
                    with ui.show_spinner("Instalando mod..."):
                        ok, msg = im.install_mod(tgt, url, file)
                    if ok: ui.print_success(msg)
                    else: ui.print_error(msg)
            
            ui.print_separator()

        except KeyboardInterrupt:
            break
        except Exception as e:
            ui.print_error(f"Error Loop: {e}")
            if debug_mode:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()