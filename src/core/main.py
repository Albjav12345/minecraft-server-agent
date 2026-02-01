"""
MineGenesis V6.0 - Main Orchestrator
Dual manager system: Client instances + Dedicated servers.
"""
import os
import sys
import json
import os
import sys
import json
from src.core.settings import Settings
from src.managers.instance_manager import InstanceManager
from src.managers.server_manager import ServerManager
from src.ai.llm_brain import LLMBrain
from src.api.minecraft_api import validator
import src.core.ui as ui

def main():
    # 1. EPIC STARTUP
    # Banner managed by render_dashboard later
    
    # 2. V7.0 ONBOARDING CHECK
    if not os.path.exists("config/.env") and not os.path.exists("config/settings.json"):
        import src.core.setup_wizard as setup_wizard
        setup_wizard.run_onboarding()
        
        # After wizard, clear and show banner before path config
        os.system('cls' if os.name == 'nt' else 'clear')
        settings = Settings()
        active_provider = settings.get_active_provider()
        provider_config = settings.get_provider_config(active_provider)
        ui.print_banner(model_name=active_provider.upper(), profile="Sistema Configurado")
        ui.console.print()
    else:
        settings = Settings()

    # 3. INITIALIZE AI
    active_provider = settings.get_active_provider()
    provider_config = settings.get_provider_config(active_provider)
    api_key = provider_config.get("api_key")
    
    # Debug info - remove later
    # ui.console.print(f"[dim]Debug Main: Active Provider: '{active_provider}'[/dim]")
    # ui.console.print(f"[dim]Debug Main: Provider Config keys: {list(provider_config.keys())}[/dim]")
    # ui.console.print(f"[dim]Debug Main: API Key present: {bool(api_key)}[/dim]")
    
    if not api_key:
        ui.print_warning(f"⚠️  La API Key para {active_provider.upper()} no está configurada o no se pudo cargar.")
        
        from rich.prompt import Confirm
        if Confirm.ask("¿Deseas configurarla ahora?", default=True):
            import src.core.setup_wizard as setup_wizard
            setup_wizard.run_onboarding()
            
            # Reload settings after wizard
            settings = Settings()
            active_provider = settings.get_active_provider()
            provider_config = settings.get_provider_config(active_provider)
            api_key = provider_config.get("api_key")
            
            if not api_key:
                ui.print_error("❌ Error: Aún no se detecta la API Key. Saliendo.")
                sys.exit(1)
        else:
            ui.print_error("❌ No se puede iniciar sin API Key.")
            sys.exit(1)

    # Configure Brain
    brain = LLMBrain()
    brain.configure(
        active_provider, 
        api_key, 
        provider_config.get("model")
    )
    
    # 4. INITIALIZE PATHS & MANAGERS
    instances_path = settings.get_instances_path()
    servers_path = settings.get_servers_path()
    
    im = InstanceManager(instances_path)
    sm = ServerManager(servers_path)
    
    im.validate_path()
    sm.validate_path()
    
    # 5. SCAN DATA
    instances = im.get_instances()
    servers = sm.get_servers()
    
    # 6. CLEAN CONSOLE AND SHOW FINAL BANNER BEFORE DASHBOARD
    os.system('cls' if os.name == 'nt' else 'clear')
    ui.print_banner(model_name=active_provider.upper(), profile="Sistema Listo")
    
    # 7. SMART STARTUP DASHBOARD
    ui.render_dashboard(instances, servers)
    ui.print_info("Sistema Online. Listo para órdenes.")
    
    # 7. MAIN LOOP
    current_instance = settings.get_last_instance()
    current_server = settings.get_last_server()
     
    # Validate existence
    if current_instance and not any(inst['name'] == current_instance for inst in instances):
        current_instance = None
    
    if current_server and not any(srv['name'] == current_server for srv in servers):
        current_server = None
    
    if current_instance and not any(inst['name'] == current_instance for inst in instances):
        current_instance = None
    
    if current_server and not any(srv['name'] == current_server for srv in servers):
        current_server = None
        
    while True:
        try:
            # Refresh data silently for context
            instances = im.get_instances()
            servers = sm.get_servers()
            
            # PROMPT shows active client or server
            prompt_label = "[GLOBAL]"
            if current_instance:
                prompt_label = f"[CLIENT:{current_instance}]"
            elif current_server:
                prompt_label = f"[SERVER:{current_server}]"
            
            # 1. VISUAL BREATHING ROOM (Pre-Input)
            ui.console.print() 
            user_input = ui.ask_user(f"[bold cyan]{prompt_label} >[/bold cyan]")
            
            if not user_input.strip():
                continue
            
            # 2. SEPARATOR (Turn Start)
            ui.print_separator()

            # === AI MANAGEMENT COMMANDS ===
            if user_input.lower() == "!models":
                ui.print_ai_status(settings.data["ai_providers"], settings.get_active_provider())
                
                # Interactive selection
                from rich.prompt import Prompt, Confirm
                ui.console.print()
                
                # Map provider names to numbers
                provider_list = list(settings.data["ai_providers"].keys())
                # ui.console.print("[dim]Selecciona: 1=Groq, 2=Google Gemini, 3=OpenAI, 4=Anthropic[/dim]") # REDUNDANT
                
                choice = Prompt.ask(
                    "Cambiar a [bold](número o Enter para cancelar)[/bold]",
                    default=""
                )
                
                if choice.strip():
                    try:
                        # Parse choice (1-4)
                        idx = int(choice) - 1
                        if 0 <= idx < len(provider_list):
                            selected_provider = provider_list[idx]
                            provider_config = settings.get_provider_config(selected_provider)
                            
                            # Check if has API key
                            if provider_config.get("api_key"):
                                # Switch immediately
                                settings.set_active_provider(selected_provider)
                                brain.configure(
                                    selected_provider,
                                    provider_config.get("api_key"),
                                    provider_config.get("model")
                                )
                                
                                # Clear console and show full dashboard
                                os.system('cls' if os.name == 'nt' else 'clear')
                                ui.print_banner(model_name=selected_provider.upper(), profile="Proveedor Cambiado")
                                ui.render_dashboard(im.get_instances(), sm.get_servers())
                                # Removed redundant success message
                            else:
                                # No API key - offer to configure
                                ui.print_warning(f"⚠️  {selected_provider.upper()} no tiene API Key configurada")
                                
                                if Confirm.ask("¿Configurar ahora?", default=True):
                                    import src.core.setup_wizard as setup_wizard
                                    setup_wizard.run_onboarding()
                                    
                                    # Clear console and show banner with new provider
                                    os.system('cls' if os.name == 'nt' else 'clear')
                                    
                                    # Reload settings
                                    settings = Settings()
                                    active = settings.get_active_provider()
                                    cfg = settings.get_provider_config(active)
                                    
                                    # Validate API key exists
                                    api_key = cfg.get("api_key")
                                    if not api_key:
                                        ui.print_error(f"Error: No se pudo cargar la API key para {active}")
                                        ui.print_separator()
                                        continue
                                    
                                    # Show banner and dashboard
                                    ui.print_banner(model_name=active.upper(), profile="Proveedor Actualizado")
                                    ui.render_dashboard(im.get_instances(), sm.get_servers())
                                    
                                    # Reconfigure brain properly (AFTER dash logic, but logically doesn't matter order for view)
                                    brain.configure(active, api_key, cfg.get("model"))
                                    # Removed redundant success message
                        else:
                            ui.print_error("Número inválido")
                    except ValueError:
                        ui.print_error("Entrada inválida")
                
                ui.print_separator()
                continue
                
            if user_input.lower() == "!config":
                settings.set_last_instance(None) # Reset context
                settings.set_last_server(None)
                import src.core.setup_wizard as setup_wizard
                setup_wizard.run_onboarding()
                
                # Clear console and show banner with new provider
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Reload
                settings = Settings() 
                active = settings.get_active_provider()
                cfg = settings.get_provider_config(active)
                
                # Show banner and dashboard
                ui.print_banner(model_name=active.upper(), profile="Proveedor Actualizado")
                ui.render_dashboard(im.get_instances(), sm.get_servers())
                
                # Reconfigure brain
                brain.configure(active, cfg.get("api_key"), cfg.get("model"))
                # Removed redundant success message
                
                continue
            
            if user_input.lower() == "!help":
                 ui.print_info("Comandos:\n- !models: Ver IAs\n- !config: Configurar IA\n- !exit: Salir\n- exit/quit: Salir")
                 ui.print_separator()
                 continue

            # MANUAL COMMANDS
            if user_input.lower() in ["exit", "salir", "quit"]:
                settings.set_last_instance(current_instance)
                settings.set_last_server(current_server)
                sys.exit(0)

            # AI QUERY
            ui.console.print("[dim italic]Pensando...[/dim italic]", end="\r")
            
            response = brain.query(
                user_input, 
                instances, 
                servers, 
                current_instance, 
                current_server
            )
            
            # CLEAR THINKING SPINNER
            ui.console.print(" " * 20, end="\r")
            
            # PARSE RESPONSE
            try:
                data = json.loads(response)
                
                # SILENT BRAIN: We do NOT print "thought"
                
                tool = data.get("tool")
                params = data.get("params", {})
                
                if tool == "list_all":
                    ui.render_dashboard(instances, servers)
                
                elif tool == "create_dedicated_server":
                    success, msg, path = sm.create_dedicated_server(**params)
                    if success:
                        ui.print_success(msg)
                        settings.set_last_server(params.get("name")) # Switch context
                        current_server = params.get("name")
                        current_instance = None
                        # Auto-refresh
                        servers = sm.get_servers()
                        ui.render_dashboard(instances, servers)
                    else:
                        ui.print_error(msg)
                
                elif tool == "install_plugin": # server mod/plugin
                     # AI should provide mod_id if possible for intelligence
                     success, msg = sm.install_plugin(**params)
                     if success:
                         ui.print_success(msg)
                     else:
                         ui.print_error(msg)

                # ... (Handle other existing tools) ...
                
                if "response_text" in data:
                    ui.print_ai_response(data["response_text"])
                    
            except json.JSONDecodeError:
                 ui.print_error("La IA balbuceó algo ininteligible.")
                 ui.console.print(f"[dim]Respuesta recibida: {response[:200]}...[/dim]")
                 
                 # Check if it's an API error (quota, rate limit, etc.)
                 if "Error" in response and any(keyword in response for keyword in ["quota", "QUOTA", "EXHAUSTED", "rate", "limit", "429"]):
                     ui.console.print()
                     ui.console.print("[yellow]💡 Sugerencia:[/yellow]")
                     ui.console.print("   • Usa [bold cyan]!config[/bold cyan] para configurar otro proveedor")
                     ui.console.print("   • Usa [bold cyan]!models[/bold cyan] para ver proveedores disponibles")
                     ui.console.print("   • [dim]Groq es gratis e ilimitado (https://console.groq.com/keys)[/dim]")
            
            # 3. SEPARATOR (Turn End)
            ui.print_separator()
                 
        except KeyboardInterrupt:
            print("\nCerrando...")
            sys.exit(0)
        except Exception as e:
            ui.print_error(f"Error inesperado: {e}")
            if user_input.lower() == "!models":
                ui.print_ai_status(settings.data["ai_providers"], settings.get_active_provider())
                continue
                
            if user_input.lower() == "!config":
                provider, key = ui.run_ai_wizard()
                settings.set_provider_config(provider, key)
                settings.set_active_provider(provider)
                brain.configure(provider, key)
                ui.print_success(f"Cambiado a {provider}")
                continue
            
            if user_input.lower().startswith("!use "):
                parts = user_input.split(" ")
                if len(parts) > 1:
                    target = parts[1]
                    if target in settings.data["ai_providers"]:
                        settings.set_active_provider(target)
                        cfg = settings.get_provider_config(target)
                        brain.configure(target, cfg.get("api_key"), cfg.get("model"))
                        ui.print_success(f"Cambiado a {target}")
                    else:
                        ui.print_error(f"Proveedor '{target}' no encontrado. Usa !config")
                else:
                    ui.print_error("Uso: !use <proveedor>")
                continue
            
            # MANUAL COMMANDS
            if user_input.lower() in ["exit", "salir", "quit"]:
                settings.set_last_instance(current_instance)
                settings.set_last_server(current_server)
                ui.print_success("¡Hasta luego! 👋")
                break
            
            if user_input.lower() in ["scan", "refresh", "actualizar", "list"]:
                instances = im.get_instances()
                servers = sm.get_servers()
                ui.print_dual_overview(instances, servers)
                continue
            
            if user_input.lower() == "ayuda":
                ui.console.print("""
[bold cyan]Comandos disponibles:[/bold cyan]

[bold yellow]Para CLIENTES (Jugar):[/bold yellow]
- crea perfil [nombre] [versión] - Crear perfil de cliente
- selecciona cliente [nombre] - Cambiar a cliente
- busca mod [query] - Buscar mods

[bold yellow]Para SERVIDORES (Hostear):[/bold yellow]
- crea servidor [nombre] [versión] [tipo] - Crear servidor dedicado
  Tipos: vanilla, paper, fabric
- selecciona servidor [nombre] - Cambiar a servidor
- busca plugin [query] - Buscar plugins

[bold cyan]Generales:[/bold cyan]
- list/refresh - Actualizar vista
- exit/salir - Cerrar

[dim]También puedes hablar naturalmente: "crea un servidor pvp 1.21 con paper"[/dim]
                """)
                continue
            
            # AI INTERACTION LOOP (ReAct)
            brain.clear_history() 
            ai_query = user_input
            turn_limit = 10
            
            for turn in range(turn_limit):
                # Always get fresh state for the Brain
                instances = im.get_instances()
                servers = sm.get_servers()
                
                with ui.show_spinner(" Procesando...") as progress:
                    task = progress.add_task("", total=None)
                    response = brain.query(ai_query, instances, servers, current_instance, current_server)
                
                # PARSE JSON
                try:
                    # Clean JSON string (remove markdown blocks and trailing text)
                    clean_res = response.strip()
                    if "```json" in clean_res:
                        clean_res = clean_res.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_res:
                        clean_res = clean_res.split("```")[1].split("```")[0].strip()
                    
                    data = json.loads(clean_res)
                    
                    # Display Thought (Subtle)
                    thought = data.get("thought")
                    if thought:
                        ui.console.print(f"[dim white]💭 {thought}[/dim white]")
                        
                    # Display AI response
                    if data.get("response_text"):
                        ui.print_ai_response(data["response_text"])
                    
                    # Execute tool
                    tool = data.get("tool")
                    params = data.get("params", {})
                    
                    if not tool or tool == "none":
                        break
                        
                    # TOOL EXECUTION
                    ui.console.print(f"[dim blue]⚙ Ejecutando herramienta: {tool}[/dim blue]")
                    tool_result = ""
                    
                    # CLIENT TOOLS
                    if tool == "create_client_profile":
                        name = params.get("name", "Client_001")
                        version = params.get("version")
                        loader = params.get("loader", "fabric")
                        is_valid, error_msg = validator.validate_version(version)
                        if not is_valid:
                            tool_result = error_msg
                        else:
                            success, msg, path = im.create_instance(name, version, loader)
                            tool_result = msg
                            if success:
                                current_instance = name
                                current_server = None
                                ui.print_dual_overview(im.get_instances(), servers)
                    
                    elif tool == "select_client":
                        name = params.get("name")
                        if any(inst['name'] == name for inst in im.get_instances()):
                            current_instance = name
                            current_server = None
                            tool_result = f"Cliente activo: {name}"
                            ui.print_success(tool_result)
                        else:
                            tool_result = f"Error: Cliente '{name}' no encontrado"
                            ui.print_error(tool_result)

                    elif tool == "list_mods":
                        instance_name = params.get("instance_name")
                        mod_list = im.get_mod_list(instance_name)
                        if mod_list:
                            ui.print_info(f"📦 Mods detectados en '{instance_name}':")
                            for m in mod_list:
                                ui.console.print(f"  [dim]- {m}[/dim]")
                            tool_result = f"Mods encontrados en '{instance_name}': {', '.join(mod_list)}"
                        else:
                            tool_result = f"No se encontraron mods en '{instance_name}' o la instancia no existe"
                            ui.print_warning(tool_result)

                    elif tool == "install_mod":
                        instance_name = params.get("instance_name")
                        url = params.get("url")
                        filename = params.get("filename")
                        if not url or not filename:
                            tool_result = "Error: Faltan parámetros de instalación (url/filename)"
                        else:
                            with ui.show_spinner(f"⬇ Descargando {filename}...") as progress:
                                task = progress.add_task("", total=None)
                                success, msg = im.install_mod(instance_name, url, filename)
                            tool_result = msg
                            if success: ui.print_success(msg)
                            else: ui.print_error(msg)
                    
                    elif tool == "install_plugin":
                        server_name = params.get("server_name")
                        url = params.get("url")
                        filename = params.get("filename")
                        if not url or not filename:
                            tool_result = "Error: Faltan parámetros de instalación"
                        else:
                            with ui.show_spinner(f"⬇ Descargando {filename}...") as progress:
                                task = progress.add_task("", total=None)
                                success, msg = sm.install_plugin(server_name, url, filename)
                            tool_result = msg
                            if success: ui.print_success(msg)
                            else: ui.print_error(msg)
                    
                    # SERVER TOOLS
                    elif tool == "create_dedicated_server":
                        name = params.get("name", "Server_001")
                        version = params.get("version")
                        server_type = params.get("server_type", "vanilla")
                        is_valid, error_msg = validator.validate_version(version)
                        if not is_valid:
                            tool_result = error_msg
                        elif server_type.lower() not in ["vanilla", "paper", "fabric"]:
                            tool_result = f"Error: Tipo '{server_type}' inválido"
                        else:
                            ui.print_info(f"Descargando {server_type} server.jar for {version}...")
                            with ui.show_spinner(f"📥 Creando servidor dedicado...") as progress:
                                task = progress.add_task("", total=None)
                                success, msg, path = sm.create_dedicated_server(name, version, server_type)
                            tool_result = msg
                            if success:
                                ui.print_success(msg)
                                current_server = name
                                current_instance = None
                                ui.print_dual_overview(instances, sm.get_servers())
                    
                    elif tool == "select_server":
                        name = params.get("name")
                        if any(srv['name'] == name for srv in sm.get_servers()):
                            current_server = name
                            current_instance = None
                            tool_result = f"Servidor activo: {name}"
                            ui.print_success(tool_result)
                        else:
                            tool_result = f"Error: Servidor '{name}' no encontrado"
                    
                    elif tool == "search_mod":
                        query = params.get("query")
                        # We use the explicitly selected instance or the first found version
                        v = "1.21.6" # Default target if unknown
                        if current_instance:
                            inst_data = next((i for i in im.get_instances() if i['name'] == current_instance), None)
                            if inst_data: v = inst_data.get('version', v)
                        
                        with ui.show_spinner(f"🔍 Buscando '{query}' compatible con {v}...") as progress:
                            results = validator.search_mod(query, v, "fabric")
                            
                        if not results:
                            tool_result = f"No se encontraron mods para '{query}' en {v}"
                        else:
                            # In ReAct mode, if it's an automation, we might auto-select if confident?
                            # For safety, we keep the confirmation for now.
                            install, s_idx = ui.confirm_mod_installation(results)
                            if install and s_idx is not None:
                                sm_mod = results[s_idx]
                                with ui.show_spinner("📥 Obteniendo descarga...") as progress:
                                    dl = validator.get_mod_download(sm_mod['slug'], v, "fabric")
                                if dl:
                                    success, msg = im.install_mod(current_instance or "Client", dl['url'], dl['filename'])
                                    tool_result = f"Instalación de {query}: {msg}"
                                else: tool_result = f"Error al obtener descarga para {query}"
                            else: tool_result = f"Instalación de {query} cancelada"

                    elif tool == "list_all":
                        ui.print_dual_overview(im.get_instances(), sm.get_servers())
                        tool_result = "Dashboard mostrado al usuario."
                    
                    # Prepara el siguiente paso del ReAct
                    ai_query = f"SISTEMA: El resultado de la herramienta '{tool}' fue: {tool_result}. Prosigue si es necesario o despídete."
                    
                except json.JSONDecodeError:
                    ui.print_error(f"Error: Respuesta de la IA no es un JSON válido.\nRaw: {response[:100]}...")
                    break

        except KeyboardInterrupt:
            settings.set_last_instance(current_instance)
            settings.set_last_server(current_server)
            ui.print_success("\n¡Hasta luego! 👋")
            break
        except Exception as e:
            ui.print_error(f"Error crítico: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
