import argparse
import sys
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.scraper import download_and_save_event
from src.exporter import export_to_excel
from src.storage import (
    has_local_event_data, load_event_data, get_event_json_path,
    get_event_config_path, get_event_profiles_path, has_event_profiles,
    load_event_profiles, get_last_active_event, set_last_active_event
)
from src.team_manager import (
    get_or_set_team_config, load_or_create_profiles,
    generate_default_profiles, calculate_roles_distribution
)
from src.xwing_db import build_xwing_database

def print_banner():
    print("=" * 68)
    print(" 🏆 LONGSHANKS TOURNAMENT SCRAPPER & WTC MATRIX GENERATOR")
    print("=" * 68)

def select_reference_team_menu(event_id: str, event_data: dict) -> str:
    teams = event_data.get('teams', [])
    if not teams:
        print("[!] No se encontraron equipos en los datos del evento.")
        return ""
        
    print("\n--- SELECCIONA TU EQUIPO DE REFERENCIA (NUESTRO EQUIPO) ---")
    for i, t in enumerate(teams, 1):
        p_count = len(t.get('players_data', [])) or len(t.get('players', []))
        print(f" [{i:2d}] {t.get('team_name')} ({p_count} jugadores)")
        
    sel = input(f"\nElige el número de tu equipo [1-{len(teams)}]: ").strip()
    try:
        idx = int(sel) - 1
        if 0 <= idx < len(teams):
            chosen = teams[idx].get('team_name')
            cfg = get_or_set_team_config(event_id, event_data, reference_team_name=chosen)
            generate_default_profiles(event_id, event_data, chosen)
            print(f"[+] Equipo de referencia fijado a: '{chosen}'")
            print(f"[+] Configuración: {cfg.get('team_size')} jugadores ({cfg.get('num_shields')} Escudos / {cfg.get('num_spears')} Lanzas)")
            return chosen
    except Exception as e:
        print(f"[!] Entrada no válida: {e}")
    return ""

def view_profiles_summary(event_id: str, event_data: dict):
    config = get_or_set_team_config(event_id, event_data)
    ref_team = config.get('reference_team', '')
    profiles = load_or_create_profiles(event_id, event_data, ref_team)
    
    print(f"\n📋 FICHAS DE PERFILADO PARA: {ref_team}")
    print(f"   Archivo editable: {get_event_profiles_path(event_id)}")
    print("-" * 68)
    for p in profiles.get('players', []):
        print(f" • {p.get('alias')} ({p.get('player_name')} - {p.get('faction')})")
        print(f"   Arquetipo: {p.get('archetype')}")
        print(f"   🟢 Favorable vs: {', '.join(p.get('favorable', [])) or 'Estándar'}")
        print(f"   🔴 Desfavorable vs: {', '.join(p.get('unfavorable', [])) or 'Ninguno'}")
        print(f"   📝 Notas: {p.get('custom_notes')}")
        if p.get('tactical_advisor'):
            print(f"   💡 Advisor Táctico: {p.get('tactical_advisor')}")
        print()
    print("[TIP] Puedes editar 'data/event_" + event_id + "_profiles.json' con cualquier editor")
    print("      o conversar conmigo para afinar notas, fortalezas y debilidades.")

def menu(active_event_id: str):
    while True:
        print_banner()
        json_exists = has_local_event_data(active_event_id)
        status_str = "[DISPONIBLE LOCALMENTE]" if json_exists else "[NO DESCARGADO]"
        
        event_data = load_event_data(active_event_id) if json_exists else {'teams': []}
        config = get_or_set_team_config(active_event_id, event_data) if json_exists else {}
        ref_team = config.get('reference_team', '[NO SELECCIONADO]')
        t_size = config.get('team_size', 5)
        n_shields = config.get('num_shields', 2)
        n_spears = config.get('num_spears', 3)
        
        has_prof = has_event_profiles(active_event_id)
        prof_str = f"[LISTAS PERFILADAS ({t_size}P)]" if has_prof else "[SIN PERFILAR]"
        
        print(f" Torneo Activo:       Evento #{active_event_id}")
        print(f" Estado Local:        {status_str}")
        print(f" Nuestro Equipo:      {ref_team}")
        print(f" Formato de Equipo:   {t_size} Jugadores ({n_shields} Escudos / {n_spears} Lanzas)")
        print(f" Fichas de Listas:    {prof_str}")
        print("-" * 68)
        print(" [1] Descargar/Actualizar datos del torneo desde Longshanks")
        print(" [2] Generar archivo Excel (.xlsx) con Matrices y Asistente WTC")
        print(" [3] Flujo Completo: Descargar datos y Generar Excel (.xlsx)")
        print(" [4] Cambiar ID del evento (Actual: #" + active_event_id + ")")
        print(" [5] Seleccionar / Cambiar Equipo de Referencia (Nuestro Equipo)")
        print(" [6] Ver / Regenerar Fichas de Listas de Nuestro Equipo")
        print(" [7] Ajustar tamaño de equipo manualmente (3, 5 o 7 jugadores)")
        print(" [8] Actualizar Base de Datos canónica de X-Wing (xwing-data2)")
        print(" [0] Salir")
        print("=" * 68)
        
        choice = input("Selecciona una opción [0-8]: ").strip()
        print()
        
        if choice == "1":
            print(f"[*] Iniciando descarga desde Longshanks para el evento #{active_event_id}...")
            data = download_and_save_event(active_event_id)
            get_or_set_team_config(active_event_id, data)
            print("[+] Descarga completada.")
            input("\nPresiona Enter para volver al menú...")
            
        elif choice == "2":
            if not json_exists:
                print(f"[!] No existen datos locales para el evento #{active_event_id}.")
                print("    Utiliza primero la opción 1 para descargarlo de Longshanks.")
            else:
                data = load_event_data(active_event_id)
                out_path = export_to_excel(active_event_id, data)
                print(f"\n[SUCCESS] Archivo Excel generado en: {out_path}")
            input("\nPresiona Enter para volver al menú...")

        elif choice == "3":
            print(f"[*] Ejecutando descarga completa y generación de Excel para #{active_event_id}...")
            data = download_and_save_event(active_event_id)
            get_or_set_team_config(active_event_id, data)
            out_path = export_to_excel(active_event_id, data)
            print(f"\n[SUCCESS] ¡Flujo completo completado! Excel disponible en: {out_path}")
            input("\nPresiona Enter para volver al menú...")
            
        elif choice == "4":
            new_id = input("Introduce el nuevo ID de evento de Longshanks: ").strip()
            if new_id:
                active_event_id = new_id
                set_last_active_event(active_event_id)
                print(f"[+] Evento activo cambiado y guardado como predeterminado: #{active_event_id}")
            input("\nPresiona Enter para volver al menú...")

        elif choice == "5":
            if not json_exists:
                print("[!] Descarga primero el torneo con la opción 1 para ver los equipos.")
            else:
                select_reference_team_menu(active_event_id, event_data)
            input("\nPresiona Enter para volver al menú...")

        elif choice == "6":
            if not json_exists:
                print("[!] Descarga primero el torneo con la opción 1.")
            else:
                view_profiles_summary(active_event_id, event_data)
                regen = input("\n¿Deseas regenerar el análisis táctico y las propuestas de la IA? (s/n)\n(Las notas personalizadas del usuario se preservarán íntegramente): ").strip().lower()
                if regen == 's':
                    ref_t = config.get('reference_team')
                    generate_default_profiles(active_event_id, event_data, ref_t)
                    print("[+] Fichas actualizadas exitosamente.")
            input("\nPresiona Enter para volver al menú...")

        elif choice == "7":
            new_ts = input("Introduce el tamaño de los equipos (3, 5 o 7): ").strip()
            if new_ts in ('3', '5', '7'):
                cfg = get_or_set_team_config(active_event_id, event_data, team_size=int(new_ts))
                ref_t = cfg.get('reference_team')
                if json_exists and ref_t:
                    generate_default_profiles(active_event_id, event_data, ref_t)
                print(f"[+] Tamaño fijado en {new_ts} jugadores.")
            else:
                print("[!] Tamaño debe ser impar: 3, 5 o 7 jugadores.")
            input("\nPresiona Enter para volver al menú...")

        elif choice == "8":
            print("[*] Descargando y actualizando base de datos canónica de X-Wing (xwing-data2)...")
            build_xwing_database(verbose=True)
            input("\nPresiona Enter para volver al menú...")

        elif choice == "0":
            print("¡Hasta pronto!")
            sys.exit(0)
        else:
            print("Opción no válida. Inténtalo de nuevo.")
            input("\nPresiona Enter para continuar...")

def main():
    saved_event_id = get_last_active_event("37716")
    parser = argparse.ArgumentParser(description="Longshanks Tournament Scraper & WTC Team Matrix Generator")
    parser.add_argument("--event", type=str, default=None, help=f"ID del evento de Longshanks (actual: #{saved_event_id})")
    parser.add_argument("--ref-team", type=str, default=None, help="Nombre del equipo de referencia (nuestro equipo)")
    parser.add_argument("--team-size", type=int, choices=[3, 5, 7], default=None, help="Número de integrantes (3, 5 o 7)")
    parser.add_argument("--download", action="store_true", help="Descargar de Longshanks y guardar JSON local")
    parser.add_argument("--excel", action="store_true", help="Generar archivo local en Excel (.xlsx)")
    parser.add_argument("--all", action="store_true", help="Descargar de Longshanks y generar Excel (.xlsx)")
    parser.add_argument("--update-db", action="store_true", help="Descargar y compilar base de datos canónica de X-Wing")
    
    args = parser.parse_args()
    if args.update_db:
        build_xwing_database(verbose=True)
        sys.exit(0)
        
    if args.event:
        event_id = args.event
        set_last_active_event(event_id)
    else:
        event_id = saved_event_id
    
    if args.download or args.all:
        print(f"[*] Descargando evento #{event_id}...")
        data = download_and_save_event(event_id)
    elif has_local_event_data(event_id):
        data = load_event_data(event_id)
    else:
        data = {'teams': []}
        
    if args.ref_team or args.team_size:
        get_or_set_team_config(event_id, data, reference_team_name=args.ref_team, team_size=args.team_size)
        
    if args.excel or args.all:
        out_path = export_to_excel(event_id, data)
        print(f"[SUCCESS] Excel guardado en: {out_path}")
        sys.exit(0)
        
    if not (args.download or args.excel or args.all or args.update_db):
        menu(event_id)

if __name__ == "__main__":
    main()
