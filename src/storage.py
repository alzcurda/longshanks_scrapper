import os
import json
from src.config import DATA_DIR, OUTPUT_DIR

def get_event_json_path(event_id: str) -> str:
    """Devuelve la ruta absoluta del archivo JSON de un evento."""
    return os.path.join(DATA_DIR, f"event_{event_id}.json")

def get_event_excel_path(event_id: str) -> str:
    """Devuelve la ruta absoluta del archivo Excel generado de un evento."""
    return os.path.join(OUTPUT_DIR, f"event_{event_id}_listas.xlsx")

def has_local_event_data(event_id: str) -> bool:
    """Comprueba si ya existen datos locales para el evento dado."""
    path = get_event_json_path(event_id)
    return os.path.exists(path) and os.path.getsize(path) > 0

def save_event_data(event_id: str, data: dict) -> str:
    """Guarda los datos brutos del evento en un archivo JSON local."""
    path = get_event_json_path(event_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[+] Datos del evento #{event_id} guardados localmente en: {path}")
    return path

def load_event_data(event_id: str) -> dict:
    """Carga los datos brutos del evento desde el JSON local."""
    path = get_event_json_path(event_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existen datos locales guardados para el evento #{event_id} ({path})")
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
