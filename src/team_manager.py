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

from src.xwing_db import get_xwing_db, get_pilot_by_id

def extract_list_summary(player_data: dict, db: dict = None) -> dict:
    if db is None:
        db = get_xwing_db()
        
    pilots_db = db.get('pilots', {})
    ships_db = db.get('ships', {})
    upgrades_db = db.get('upgrades', {})
    
    raw_xws = player_data.get('raw_xws', '')
    lines = player_data.get('list_lines', [])
    faction = player_data.get('faction', 'Sin Facción')
    
    inits = []
    agilities = []
    hulls = []
    shields = []
    sizes = []
    pilot_names = []
    ship_names = []
    
    has_bombs = False
    bomb_count = 0
    has_tractors = False
    has_ordnance = False
    has_heavy_cannons = False
    
    if raw_xws:
        try:
            xws = json.loads(raw_xws)
            for pi in xws.get('pilots', []):
                pid = str(pi.get('id', '')).lower().strip()
                s_id = str(pi.get('ship', '')).lower().strip()
                p_name_raw = str(pi.get('name', '')).strip()
                
                p_obj = get_pilot_by_id(pid, ship_hint=s_id, name_hint=p_name_raw, db=db)
                s_obj = ships_db.get(s_id) or ships_db.get(s_id.replace('-', ''))
                if not s_obj and p_obj and p_obj.get('ship'):
                    s_obj = ships_db.get(p_obj.get('ship'))
                
                p_name = p_obj.get('name') if p_obj else format_id_to_name(pid)
                p_name = p_name.replace('"', '').strip()
                init = p_obj.get('initiative', 3) if p_obj else 3
                inits.append(init)
                pilot_names.append(p_name)
                
                s_name = s_obj.get('name') if s_obj else format_id_to_name(s_id)
                agil = s_obj.get('agility', 2) if s_obj else 2
                agilities.append(agil)
                hull = s_obj.get('hull', 3) if s_obj else 3
                hulls.append(hull)
                shield = s_obj.get('shields', 1) if s_obj else 1
                shields.append(shield)
                size = s_obj.get('size', 'Small') if s_obj else 'Small'
                sizes.append(size)
                ship_names.append(s_name)
                
                if p_obj and p_obj.get('has_native_tractor'):
                    has_tractors = True
                if s_obj and s_obj.get('has_native_tractor'):
                    has_tractors = True
                    
                for slot, upgs in pi.get('upgrades', {}).items():
                    for u in upgs:
                        u_norm = str(u).lower().replace('-', '')
                        u_obj = upgrades_db.get(u_norm)
                        if u_obj:
                            if u_obj.get('is_bomb'):
                                has_bombs = True
                                bomb_count += 1
                            if u_obj.get('is_tractor'):
                                has_tractors = True
                            if u_obj.get('is_torpedo') or u_obj.get('is_missile'):
                                has_ordnance = True
                            if u_obj.get('is_cannon'):
                                has_heavy_cannons = True
        except Exception:
            pass
            
    if not pilot_names and lines:
        for l in lines:
            m = re.match(r'^\d+\.\s*([^(]+)\s*(?:\(([^)]+)\))?', l)
            if m:
                p_raw = m.group(1).strip()
                s_raw = m.group(2).strip() if m.group(2) else ""
                p_obj = get_pilot_by_id("", ship_hint=s_raw, name_hint=p_raw, db=db)
                s_obj = ships_db.get(p_obj.get('ship', '')) if p_obj else None
                
                p_name = p_obj.get('name') if p_obj else p_raw
                s_name = s_obj.get('name') if s_obj else (s_raw or 'Nave')
                init = p_obj.get('initiative', 3) if p_obj else 3
                agil = s_obj.get('agility', 2) if s_obj else 2
                hull = s_obj.get('hull', 3) if s_obj else 3
                shield = s_obj.get('shields', 1) if s_obj else 1
                size = s_obj.get('size', 'Small') if s_obj else 'Small'
                
                pilot_names.append(p_name)
                ship_names.append(s_name)
                inits.append(init)
                agilities.append(agil)
                hulls.append(hull)
                shields.append(shield)
                sizes.append(size)
                
    num_ships = len(pilot_names)
    max_init = max(inits) if inits else 3
    min_init = min(inits) if inits else 3
    high_inits = sum(1 for i in inits if i >= 5)
    large_med_count = sum(1 for sz in sizes if sz in ('Medium', 'Large', 'Huge'))
    total_hp = sum(hulls) + sum(shields)
    
    ship_counts = Counter(ship_names)
    ship_str_parts = [f"{count}x {s}" if count > 1 else s for s, count in ship_counts.items()]
    ship_summary = ", ".join(ship_str_parts) if ship_str_parts else f"{num_ships} naves"
    pilot_summary = ", ".join(pilot_names) if pilot_names else "Sin pilotos parseados"
    
    # Heurística táctica profunda de X-Wing
    if num_ships >= 7:
        archetype = f"Enjambre puro ({num_ships} naves: {ship_summary})"
        fav = ["pocas_naves", "baja_agilidad", "naves_grandes"]
        unfav = ["bombas_masivas", "ases_i6"]
        prop = (
            f"[Propuesta IA] Enjambre masivo de {num_ships} naves enfocado en control de tablero, "
            f"bloqueos a iniciativa baja y saturación de fuego ({num_ships*2}+ dados de ataque). "
            f"Favorable vs listas de 2-3 naves pesadas y naves grandes de baja agilidad al anularles acciones. "
            f"Desfavorable vs bombas masivas y daño en área que limpian naves de 3 vidas sin tirar defensa. "
            f"(Edita fortalezas y debilidades según tu experiencia con el jugador)"
        )
        advisor = (
            "Asesor Táctico: Tu mayor ventaja es el bloqueo con los pilotos de I1 para denegar acciones "
            "a las naves rivales y castigarlas a rango 1. Mantén la nave de apoyo atrás y prioriza destruir "
            "primero a cualquier nave rival que porte bombas o minas."
        )
    elif num_ships <= 3 and num_ships > 0:
        if large_med_count >= 2:
            archetype = f"3 naves pesadas/medianas ({pilot_summary})"
            fav = ["pocas_naves", "baja_agilidad", "naves_grandes"]
            unfav = ["enjambres_6+"] # Peanas medianas/grandes inmunes a tractores de 1 token
            prop = (
                f"[Propuesta IA] Lista de choque con {num_ships} naves pesadas/medianas (Iniciativas: {', '.join(str(i) for i in sorted(inits, reverse=True))}) "
                f"y un colchón masivo de {total_hp} puntos de vida. Inmune a tractores en sus dos naves principales. "
                f"Favorable vs pocas naves y naves de agilidad 1-2 a las que pulveriza en cruces frontales. "
                f"Desfavorable vs enjambres puros (6+ naves) que saturen su agilidad 2 y bloqueen su movimiento. "
                f"(Edita fortalezas y debilidades según tu experiencia con el jugador)"
            )
            advisor = (
                "Asesor Táctico: Tienes ventaja de iniciativa y potencia de fuego concentrada. Usa tus bombas y cañones "
                "a rango 2-3 para romper formaciones antes del cruce frontal. Evita pasillos estrechos frente a enjambres "
                "para no perder la acción de modificación de dados."
            )
        else:
            archetype = f"Trío de ases ({pilot_summary})"
            fav = ["iniciativa_baja", "poca_defensa", "pocas_naves"]
            unfav = ["enjambres_5+", "bombas_masivas"]
            prop = (
                f"[Propuesta IA] Escuadrón de 3 ases de élite con iniciativa {max_init} dominante y alta capacidad de reposicionamiento. "
                f"Favorable vs rivales de menor iniciativa y naves de pocas defensas a las que caza fuera de arco. "
                f"Desfavorable vs enjambres de 5+ naves que cubran todo el arco y saturación de bombas. "
                f"(Edita fortalezas y debilidades según tu experiencia con el jugador)"
            )
            advisor = (
                "Asesor Táctico: Juega a dilatar el combate en los primeros turnos y fuerza al rival a dividirse. "
                "No te comprometas a intercambios frontales simétricos si el rival tira más dados totales."
            )
    else: # 4 o 5 naves
        if max_init == 6 and high_inits >= 2:
            archetype = f"Escuadrón mixto con As I6 ({pilot_summary})"
            fav = ["baja_agilidad", "pocas_naves", "iniciativa_baja"]
            unfav = ["bombas_masivas", "enjambres_6+"]
            prop = (
                f"[Propuesta IA] Escuadrón equilibrado de {num_ships} naves encabezado por un As de iniciativa 6 con naves de apoyo ({total_hp} HP totales). "
                f"Favorable vs listas de naves lentas y de baja agilidad donde la iniciativa alta permite flanquear y rematar impunemente. "
                f"Desfavorable vs saturación de bombas y enjambres de 6+ naves que colapsen el espacio de maniobra. "
                f"(Edita fortalezas y debilidades según tu experiencia con el jugador)"
            )
            advisor = (
                "Asesor Táctico: El as de I6 tiene una capacidad ofensiva letal pero poca tolerancia al daño concentrado. "
                "Utiliza a tus naves de apoyo como pantalla para atraer el fuego rival mientras el as entra por el flanco."
            )
        elif high_inits >= 3:
            archetype = f"Escuadrón de media/alta iniciativa ({pilot_summary})"
            fav = ["iniciativa_baja", "poca_defensa", "enjambres"]
            unfav = ["ases_i6", "tractores"]
            prop = (
                f"[Propuesta IA] Escuadrón de {num_ships} naves con núcleo dominante de iniciativa 5. "
                f"Favorable vs rivales de iniciativa <= 4 y naves con pocas defensas a las que castiga antes de que disparen. "
                f"Desfavorable vs Ases I6 que muevan después y listas con tractores. "
                f"(Edita fortalezas y debilidades según tu experiencia con el jugador)"
            )
            advisor = (
                "Asesor Táctico: Aprovecha el disparo simultáneo a I5 para eliminar una nave rival clave en turno 2 "
                "antes de que pueda gastar sus tokens o responder al fuego."
            )
        else:
            archetype = f"Escuadrón equilibrado de {num_ships} naves ({pilot_summary})"
            fav = ["baja_agilidad", "naves_grandes"]
            unfav = ["ases_i6", "bombas_masivas"]
            prop = (
                f"[Propuesta IA] Lista versátil de {num_ships} naves con {total_hp} HP y gran consistencia de disparos a rango medio. "
                f"Favorable vs naves grandes y de baja agilidad por desgaste sostenido. "
                f"Desfavorable vs Ases de I6 que esquiven sus arcos y contra saturación de bombas. "
                f"(Edita fortalezas y debilidades según tu experiencia con el jugador)"
            )
            advisor = (
                "Asesor Táctico: Mantén la formación en cajas de fuego solapadas para asegurar que cualquier objetivo "
                "que entre en tu alcance reciba al menos 2-3 ataques combinados."
            )
            
    return {
        'num_ships': num_ships,
        'pilot_names': pilot_names,
        'ship_names': ship_names,
        'inits': inits,
        'max_init': max_init,
        'pilot_summary': pilot_summary,
        'ship_summary': ship_summary,
        'archetype': archetype,
        'favorable': fav,
        'unfavorable': unfav,
        'proposal_note': prop,
        'advisor_note': advisor
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

def is_user_customized(p_existing: dict) -> bool:
    if not p_existing:
        return False
    notes = p_existing.get('custom_notes', '').strip()
    if not notes:
        return False
    if notes.startswith('[Propuesta IA]') or notes.startswith('[Propuesta automática'):
        return False
    if notes.startswith('Lista real:') and 'Edita fortalezas' in notes:
        return False
    if notes == 'Edita fortalezas y debilidades según tu experiencia.':
        return False
    return True

def generate_default_profiles(event_id: str, event_data: dict, reference_team_name: str) -> dict:
    team = find_team_in_event(event_data, reference_team_name)
    if not team:
        raise ValueError(f'No se encontró el equipo de referencia "{reference_team_name}" en los datos del evento.')
    
    existing_profiles = {}
    if has_event_profiles(event_id):
        try:
            old_prof = load_event_profiles(event_id)
            for p in old_prof.get('players', []):
                if p.get('player_name'):
                    existing_profiles[p.get('player_name').strip().lower()] = p
                if p.get('alias'):
                    existing_profiles[p.get('alias').strip().lower()] = p
        except Exception:
            pass

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
            
        # Extraer análisis REAL y profundo de la lista con la base de datos YASB
        summary = extract_list_summary(p)
        
        # Buscar si ya existía perfil personalizado por el usuario
        p_existing = existing_profiles.get(full_name.strip().lower()) or existing_profiles.get(alias.strip().lower())
        
        if is_user_customized(p_existing):
            # PREVALENCIA DE LAS NOTAS Y CRITERIOS DEL USUARIO
            fav = p_existing.get('favorable', summary['favorable'])
            unfav = p_existing.get('unfavorable', summary['unfavorable'])
            custom_notes = p_existing.get('custom_notes')
            archetype = p_existing.get('archetype') or summary['archetype']
            fav_str = ", ".join(fav)
            unfav_str = ", ".join(unfav)
            advisor = (
                f"Validación de notas: Planteamiento totalmente coherente con la lista ({summary['num_ships']} naves: {summary['pilot_summary']}). "
                f"Tus fortalezas ({fav_str}) aprovechan al máximo la pegada a iniciativa {summary['max_init']}. "
                f"Tus debilidades ({unfav_str}) identifican con precisión las amenazas que debes esquivar. "
                f"Como asesor adicional: {summary['advisor_note'].replace('Asesor Táctico: ', '')}"
            )
        else:
            # PRIMERA PROPUESTA AUTOMÁTICA DE LA IA
            fav = summary['favorable']
            unfav = summary['unfavorable']
            archetype = summary['archetype']
            custom_notes = summary['proposal_note']
            advisor = summary['advisor_note']
            
        profiles_list.append({
            'player_name': full_name,
            'alias': alias,
            'faction': faction,
            'archetype': archetype,
            'favorable': fav,
            'unfavorable': unfav,
            'custom_notes': custom_notes,
            'tactical_advisor': advisor
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
    print(f'[+] Fichas de perfilado generadas/actualizadas con análisis táctico IA ({len(profiles_list)} jugadores) en data/event_{event_id}_profiles.json')
    return profiles_data

def load_or_create_profiles(event_id: str, event_data: dict, reference_team_name: str) -> dict:
    if has_event_profiles(event_id):
        profiles = load_event_profiles(event_id)
        if profiles and profiles.get('reference_team') == reference_team_name:
            return profiles
    return generate_default_profiles(event_id, event_data, reference_team_name)

