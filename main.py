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
from src.gsheet_exporter import export_to_gsheet
from src.storage import has_local_event_data, load_event_data, get_event_json_path

def print_banner():
    print("=" * 65)
    print(" 🏆 LONGSHANKS TOURNAMENT SCRAPPER & GOOGLE SHEETS GENERATOR")
    print("=" * 65)

def menu(active_event_id: str):
    while True:
        print_banner()
        json_exists = has_local_event_data(active_event_id)
        status_str = "[DISPONIBLE LOCALMENTE]" if json_exists else "[NO DESCARGADO]"
        
        print(f" Torneo Activo: Evento #{active_event_id}")
        print(f" Estado Local:  {status_str} ({get_event_json_path(active_event_id)})")
        print("-" * 65)
        print(" [1] Descargar/Actualizar datos del torneo desde Longshanks (Guardar local)")
        print(" [2] Generar GOOGLE SHEET directamente online (Instantáneo desde datos locales)")
        print(" [3] Flujo Completo: Descargar y Crear GOOGLE SHEET directamente online")
        print(" [4] Generar copia de respaldo local en Excel (.xlsx)")
        print(" [5] Cambiar ID del evento (Actual: #" + active_event_id + ")")
        print(" [0] Salir")
        print("=" * 65)
        
        choice = input("Selecciona una opción [0-5]: ").strip()
        print()
        
        if choice == "1":
            print(f"[*] Iniciando descarga desde Longshanks para el evento #{active_event_id}...")
            download_and_save_event(active_event_id)
            print("[+] Descarga completada. Ya puedes generar tu Google Sheet con la opción 2.")
            input("\nPresiona Enter para volver al menú...")
            
        elif choice == "2":
            if not json_exists:
                print(f"[!] No existen datos locales para el evento #{active_event_id}.")
                print("    Por favor, utiliza primero la opción 1 para descargarlo de Longshanks.")
            else:
                print(f"[*] Cargando datos locales de data/event_{active_event_id}.json...")
                data = load_event_data(active_event_id)
                try:
                    url = export_to_gsheet(active_event_id, data)
                    print(f"\n🎉 ¡Google Sheet disponible directamente!")
                    print(f"🔗 Enlace: {url}")
                except Exception as e:
                    print(f"\n[ERROR] {e}")
            input("\nPresiona Enter para volver al menú...")
            
        elif choice == "3":
            print(f"[*] Ejecutando descarga y creación directa de Google Sheet para #{active_event_id}...")
            data = download_and_save_event(active_event_id)
            try:
                url = export_to_gsheet(active_event_id, data)
                print(f"\n🎉 ¡Google Sheet listo para compartir!")
                print(f"🔗 Enlace: {url}")
            except Exception as e:
                print(f"\n[ERROR] {e}")
            input("\nPresiona Enter para volver al menú...")

        elif choice == "4":
            if not json_exists:
                data = download_and_save_event(active_event_id)
            else:
                data = load_event_data(active_event_id)
            out_path = export_to_excel(active_event_id, data)
            print(f"[SUCCESS] Copia en Excel guardada en: {out_path}")
            input("\nPresiona Enter para volver al menú...")
            
        elif choice == "5":
            new_id = input("Introduce el nuevo ID de evento de Longshanks: ").strip()
            if new_id:
                active_event_id = new_id
                print(f"[+] Evento activo cambiado a #{active_event_id}")
            input("\nPresiona Enter para volver al menú...")
            
        elif choice == "0":
            print("¡Hasta pronto!")
            sys.exit(0)
        else:
            print("Opción no válida. Inténtalo de nuevo.")
            input("\nPresiona Enter para continuar...")

def main():
    parser = argparse.ArgumentParser(description="Longshanks Tournament List Scraper & Direct Google Sheets Generator")
    parser.add_argument("--event", type=str, default="36216", help="ID del evento de Longshanks (ej. 36216)")
    parser.add_argument("--download", action="store_true", help="Solo descargar de Longshanks y guardar JSON local")
    parser.add_argument("--gsheet", action="store_true", help="Crear directamente el Google Sheet online")
    parser.add_argument("--excel", action="store_true", help="Generar archivo local en Excel (.xlsx)")
    
    args = parser.parse_args()
    event_id = args.event
    
    if args.download:
        print(f"[*] Descargando evento #{event_id}...")
        download_and_save_event(event_id)
        sys.exit(0)
        
    elif args.gsheet:
        if not has_local_event_data(event_id):
            data = download_and_save_event(event_id)
        else:
            data = load_event_data(event_id)
        url = export_to_gsheet(event_id, data)
        print(f"\n🔗 Google Sheet URL: {url}")
        sys.exit(0)
        
    elif args.excel:
        if not has_local_event_data(event_id):
            data = download_and_save_event(event_id)
        else:
            data = load_event_data(event_id)
        out_path = export_to_excel(event_id, data)
        print(f"[SUCCESS] Excel guardado en: {out_path}")
        sys.exit(0)

    menu(event_id)

if __name__ == "__main__":
    main()
