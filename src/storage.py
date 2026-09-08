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

def get_event_config_path(event_id: str) -> str:
    """Devuelve la ruta del archivo de configuración del evento."""
    return os.path.join(DATA_DIR, f"event_{event_id}_config.json")

def get_event_profiles_path(event_id: str) -> str:
    """Devuelve la ruta del archivo de fichas de perfilado del evento."""
    return os.path.join(DATA_DIR, f"event_{event_id}_profiles.json")

def has_event_config(event_id: str) -> bool:
    path = get_event_config_path(event_id)
    return os.path.exists(path) and os.path.getsize(path) > 0

def save_event_config(event_id: str, config: dict) -> str:
    path = get_event_config_path(event_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return path

def load_event_config(event_id: str) -> dict:
    path = get_event_config_path(event_id)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def has_event_profiles(event_id: str) -> bool:
    path = get_event_profiles_path(event_id)
    return os.path.exists(path) and os.path.getsize(path) > 0

def save_event_profiles(event_id: str, profiles: dict) -> str:
    path = get_event_profiles_path(event_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    return path

def load_event_profiles(event_id: str) -> dict:
    path = get_event_profiles_path(event_id)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_settings_path() -> str:
    """Devuelve la ruta del archivo de configuración global de la aplicación."""
    return os.path.join(DATA_DIR, "settings.json")

def load_settings() -> dict:
    """Carga los ajustes globales de la aplicación."""
    path = get_settings_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(settings: dict) -> str:
    """Guarda los ajustes globales de la aplicación."""
    path = get_settings_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    return path

def get_last_active_event(default_id: str = "36216") -> str:
    """Obtiene el último ID de evento de torneo utilizado."""
    settings = load_settings()
    return settings.get("active_event_id", default_id)

def set_last_active_event(event_id: str) -> None:
    """Guarda el ID de evento activo para que persista entre reinicios."""
    if not event_id:
        return
    settings = load_settings()
    settings["active_event_id"] = str(event_id).strip()
    save_settings(settings)

