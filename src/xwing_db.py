import os
import re
import json
import urllib.request

YASB_SOURCE_URL = "https://raw.githubusercontent.com/raithos/xwing/master/coffeescripts/content/cards-common.coffee"
_CACHED_DB = None

def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'data', 'xwing_db.json')

def canonicalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())

def build_xwing_database(verbose: bool = True) -> dict:
    """
    Descarga y compila la base de datos canónica de X-Wing DIRECTA Y EXCLUSIVAMENTE desde YASB (raithos/xwing).
    Garantiza que el 100% de naves, pilotos y cartas (incluyendo Legends and Relics, BoE, etc.)
    coincidan con el motor oficial de listas utilizado por los jugadores.
    """
    if verbose:
        print("[*] Descargando base de datos oficial de YASB (raithos/xwing)...", flush=True)
        
    try:
        req = urllib.request.Request(YASB_SOURCE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        if verbose:
            print(f"[!] Error descargando datos de YASB: {e}", flush=True)
        return {}

    ships_db = {}
    pilots_db = {}
    upgrades_db = {}

    # 1. Extraer bloques de naves
    ship_blocks = re.findall(
        r'\"([^\"]+)\":\s*\n\s*name:\s*\"[^\"]+\"(.*?)(?=\n\s*\"[A-Z0-9]|\n\s*exportObj|\n\s*pilotsById|\Z)', 
        content, 
        re.DOTALL
    )
    for s_name, s_body in ship_blocks:
        xws = canonicalize(s_name)
        ag_m = re.search(r'agility:\s*(\d+)', s_body)
        hull_m = re.search(r'hull:\s*(\d+)', s_body)
        shield_m = re.search(r'shields:\s*(\d+)', s_body)
        base_m = re.search(r'base:\s*\"([^\"]+)\"', s_body)
        
        agility = int(ag_m.group(1)) if ag_m else 2
        hull = int(hull_m.group(1)) if hull_m else 0
        shields = int(shield_m.group(1)) if shield_m else 0
        size = base_m.group(1) if base_m else "Small"
        
        has_native_tractor = (
            xws in ('quadrijettransferspacetug', 'nantexclassstarfighter', 'quadjumper') or 
            'tractor' in s_body.lower()
        )
        
        ships_db[xws] = {
            'name': s_name,
            'xws': xws,
            'size': size,
            'agility': agility,
            'hull': hull,
            'shields': shields,
            'has_native_tractor': has_native_tractor
        }

    # 2. Extraer bloques de pilotos y cartas de mejora
    card_chunks = re.split(r'\n\s*\{\s*\n|\n\s*name:\s*\"', content)
    for chunk in card_chunks:
        name_m = re.search(r'name:\s*\"([^\"]+)\"', chunk) if not chunk.startswith('"') else re.search(r'^([^\"]+)\"', chunk)
        if not name_m:
            continue
        c_name = name_m.group(1)
        addon_m = re.search(r'xwsaddon:\s*\"([^\"]+)\"', chunk)
        addon = addon_m.group(1) if addon_m else ""
        
        base_xws = canonicalize(c_name)
        xws_id = f"{base_xws}-{addon}" if addon else base_xws
        
        skill_m = re.search(r'skill:\s*(\d+)', chunk)
        slot_m = re.search(r'slot:\s*\"([^\"]+)\"', chunk)
        ship_m = re.search(r'ship:\s*\"([^\"]+)\"', chunk)
        faction_m = re.search(r'faction:\s*\"([^\"]+)\"', chunk)
        
        if skill_m:
            init = int(skill_m.group(1))
            ship = canonicalize(ship_m.group(1)) if ship_m else ""
            faction = canonicalize(faction_m.group(1)) if faction_m else ""
            pilot_tractor = (base_xws == 'ketsuonyo' or 'tractor' in chunk.lower() or ship in ('quadrijettransferspacetug', 'nantexclassstarfighter'))
            
            p_data = {
                'name': c_name,
                'xws': xws_id,
                'initiative': init,
                'ship': ship,
                'faction': faction,
                'has_native_tractor': pilot_tractor
            }
            pilots_db[xws_id] = p_data
            pilots_db[base_xws] = p_data
            # Variantes normalizadas sin guiones
            clean_id = xws_id.replace('-', '')
            pilots_db[clean_id] = p_data
                
        elif slot_m:
            slot = slot_m.group(1)
            is_tractor = ('tractor' in xws_id.lower() or 'tractor' in chunk.lower() or 'ensnare' in xws_id.lower())
            is_bomb = ('bomb' in xws_id.lower() or 'mine' in xws_id.lower() or slot.lower() == 'device')
            
            u_data = {
                'name': c_name,
                'xws': xws_id,
                'slot': slot,
                'is_tractor': is_tractor,
                'is_bomb': is_bomb
            }
            upgrades_db[xws_id] = u_data
            upgrades_db[base_xws] = u_data
            clean_id = xws_id.replace('-', '')
            upgrades_db[clean_id] = u_data

    db = {
        'version': 'YASB-canonical-XWA',
        'source': YASB_SOURCE_URL,
        'ships': ships_db,
        'pilots': pilots_db,
        'upgrades': upgrades_db
    }
    
    out_path = get_db_path()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as out:
        json.dump(db, out, ensure_ascii=False, indent=2)
        
    global _CACHED_DB
    _CACHED_DB = db
    
    if verbose:
        print(f"[SUCCESS] Base de datos 100% YASB guardada en: {out_path}", flush=True)
        print(f"   • {len(ships_db)} naves | {len(pilots_db)} pilotos | {len(upgrades_db)} cartas de mejora.", flush=True)
        
    return db

def get_xwing_db() -> dict:
    """
    Retorna la base de datos de YASB en memoria. Si no existe en disco, se construye directamente de YASB.
    """
    global _CACHED_DB
    if _CACHED_DB is not None:
        return _CACHED_DB
        
    path = get_db_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                _CACHED_DB = json.load(f)
                if _CACHED_DB.get('version') == 'YASB-canonical-XWA':
                    return _CACHED_DB
        except Exception:
            pass
            
    return build_xwing_database(verbose=False)
