import os
import re
import json
from collections import Counter
from src.storage import (
    load_event_config, save_event_config, has_event_config,
    load_event_profiles, save_event_profiles, has_event_profiles
)

def format_id_to_name(raw_id: str) -> str:
    if not raw_id:
        return ""
    # Separar guiones
    parts = raw_id.split('-')[0].replace('_', ' ')
    # Separar camelCase si existe
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', parts)
    return s.title().strip()

def extract_list_summary(player_data: dict) -> dict:
    raw_xws = player_data.get('raw_xws', '')
    lines = player_data.get('list_lines', [])
    faction = player_data.get('faction', 'Sin Facción')
    
    pilots = []
    ships = []
    has_large_ships = False
    
    if raw_xws:
        try:
            xws = json.loads(raw_xws)
            for p in xws.get('pilots', []):
                p_id = p.get('name') or p.get('id', '')
                p_ship = p.get('ship', '')
                pilots.append(format_id_to_name(str(p_id)))
                ships.append(format_id_to_name(str(p_ship)))
                if any(lg in str(p_ship).lower() for lg in ('firespray', 'gauntlet', 'yt1300', 'st70', 'decimator', 'vcx100', 'laat')):
                    has_large_ships = True
        except Exception:
            pass
            
    if not pilots and lines:
        for l in lines:
            m = re.match(r'^\d+\.\s*([^(]+)\s*\(([^)]+)\)', l)
            if m:
                pilots.append(m.group(1).strip())
                ships.append(m.group(2).strip())
                
    num_ships = len(pilots)
    
    # Resumen de naves agrupadas (ej. "1x Gauntlet Fighter, 7x TIE/ln Fighter")
    ship_counts = Counter(ships)
    ship_str_parts = [f"{count}x {s_name}" if count > 1 else s_name for s_name, count in ship_counts.items()]
    ship_summary = ", ".join(ship_str_parts) if ship_str_parts else f"{num_ships} naves"
    pilot_summary = ", ".join(pilots) if pilots else "Sin pilotos parseados"
    
    # Determinar arquetipo
    if num_ships >= 6:
        archetype = f"Enjambre de {num_ships} naves ({ship_summary})"
        fav = ["baja_agilidad", "naves_grandes"]
        unfav = ["bombas_masivas"]
        def_aff = "media"
    elif num_ships <= 3 and num_ships > 0:
        archetype = f"{num_ships} naves pesadas/ases ({pilot_summary})"
        fav = ["pocas_naves", "baja_agilidad"]
        unfav = ["enjambre_5+"]
        def_aff = "alta" if has_large_ships else "baja"
    else:
        archetype = f"{num_ships} naves ({pilot_summary})"
        fav = ["baja_agilidad", "pocas_naves"]
        unfav = ["bombas_masivas"]
        def_aff = "alta"
        
    return {
        'num_ships': num_ships,
        'pilots': pilots,
        'ships': ships,
        'pilot_summary': pilot_summary,
        'ship_summary': ship_summary,
        'archetype': archetype,
        'favorable': fav,
        'unfavorable': unfav,
        'defensive_affinity': def_aff
    }

def detect_tournament_team_size(event_data: dict) -> int:
    teams = event_data.get('teams', [])
    if not teams:
        return 5
    sizes = []
    for t in teams:
        p_count = len(t.get('players_data', [])) or len(t.get('players', []))
        if p_count in (3, 5, 7):
            sizes.append(p_count)
        elif p_count > 0:
            sizes.append(p_count)
    if not sizes:
        return 5
    most_common = Counter(sizes).most_common(1)[0][0]
    return most_common if most_common in (3, 5, 7) else 5

def calculate_roles_distribution(team_size: int) -> tuple[int, int]:
    num_shields = (team_size - 1) // 2
    num_spears = (team_size + 1) // 2
    return num_shields, num_spears

def find_team_in_event(event_data: dict, team_name_query: str) -> dict | None:
    if not team_name_query:
        return None
    q = team_name_query.strip().lower()
    for t in event_data.get('teams', []):
        t_name = t.get('team_name', '').strip().lower()
        if q == t_name or q in t_name:
            return t
    return None

def get_or_set_team_config(event_id: str, event_data: dict, reference_team_name: str = None, team_size: int = None) -> dict:
    config = load_event_config(event_id)
    updated = False
    
    if team_size:
        config['team_size'] = int(team_size)
        updated = True
    elif 'team_size' not in config:
        config['team_size'] = detect_tournament_team_size(event_data)
        updated = True
        
    ts = config['team_size']
    shields, spears = calculate_roles_distribution(ts)
    config['num_shields'] = shields
    config['num_spears'] = spears
    
    if reference_team_name:
        matched_team = find_team_in_event(event_data, reference_team_name)
        if matched_team:
            config['reference_team'] = matched_team.get('team_name')
            p_len = len(matched_team.get('players_data', [])) or len(matched_team.get('players', []))
            if p_len in (3, 5, 7) and not team_size:
                config['team_size'] = p_len
                config['num_shields'], config['num_spears'] = calculate_roles_distribution(p_len)
        else:
            config['reference_team'] = reference_team_name
        updated = True
    elif 'reference_team' not in config:
        # Buscar "Spain" o "Mudhorn" o el primer equipo
        spain_match = find_team_in_event(event_data, 'spain')
        mudhorn_match = find_team_in_event(event_data, 'mudhorn')
        target = spain_match or mudhorn_match
        if target:
            config['reference_team'] = target.get('team_name')
        else:
            teams = event_data.get('teams', [])
            if teams:
                config['reference_team'] = teams[0].get('team_name')
        updated = True

    if updated or not has_event_config(event_id):
        save_event_config(event_id, config)
        
    return config

def generate_default_profiles(event_id: str, event_data: dict, reference_team_name: str) -> dict:
    team = find_team_in_event(event_data, reference_team_name)
    if not team:
        raise ValueError(f'No se encontró el equipo de referencia "{reference_team_name}" en los datos del evento.')
    
    players_data = team.get('players_data', [])
    if not players_data:
        players_data = [{'player_name': p.get('player_name', f'Jugador {i+1}'), 'faction': 'Desconocida'} 
                        for i, p in enumerate(team.get('players', []))]
        
    team_size = len(players_data)
    if team_size not in (3, 5, 7):
        team_size = 5 if team_size == 0 else team_size
    num_shields, num_spears = calculate_roles_distribution(team_size)
    
    profiles_list = []
    for idx, p in enumerate(players_data):
        full_name = p.get('player_name', f'Jugador {idx+1}')
        faction = p.get('faction', 'Sin Facción')
        
        # Alias legible
        if 'alzcurda' in full_name.lower():
            alias = 'Alzu'
        else:
            alias = full_name.split()[0] if full_name else f'Jugador {idx+1}'
            
        # Extraer análisis REAL de la lista descargada de Longshanks
        summary = extract_list_summary(p)
        
        profiles_list.append({
            'player_name': full_name,
            'alias': alias,
            'faction': faction,
            'archetype': summary['archetype'],
            'defensive_affinity': summary['defensive_affinity'],
            'favorable': summary['favorable'],
            'unfavorable': summary['unfavorable'],
            'custom_notes': f"Lista real: {summary['pilot_summary']}. Edita fortalezas y debilidades según tu experiencia."
        })
        
    profiles_data = {
        'event_id': str(event_id),
        'reference_team': team.get('team_name', reference_team_name),
        'team_size': team_size,
        'num_shields': num_shields,
        'num_spears': num_spears,
        'players': profiles_list
    }
    save_event_profiles(event_id, profiles_data)
    print(f'[+] Fichas de perfilado generadas a partir de las listas REALES de Longshanks ({len(profiles_list)} jugadores) en data/event_{event_id}_profiles.json')
    return profiles_data

def load_or_create_profiles(event_id: str, event_data: dict, reference_team_name: str) -> dict:
    if has_event_profiles(event_id):
        profiles = load_event_profiles(event_id)
        if profiles and profiles.get('reference_team') == reference_team_name:
            return profiles
    return generate_default_profiles(event_id, event_data, reference_team_name)
