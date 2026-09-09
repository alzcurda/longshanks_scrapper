import os
import re
import json
from src.xwing_db import get_xwing_db, get_pilot_by_id

LOW_AGILITY_SHIPS = {
    'yt1300', 'customizedyt1300lightfreighter', 'vcx100lightfreighter', 
    'vt49decimator', 'btlbywing', 'ywing', 'ywing-swz82', 'laatigunship',
    'lambdaclasst4ashuttle', 'upsilonclassshuttle', 'gr75mediumtransport'
}

HIGH_INIT_BOOST_LARGE_SHIPS = {
    'hansolo', 'bobafett', 'dashrendar', 'lando-calrissian', 'rey'
}

FRAGILE_ACES = {
    'soontirfel', 'whisper', 'bobafett', 'guri', 'fennrau',
    'poedameron', 'kylo-ren'
}

INITIATIVE_6_PILOTS = {
    'darthvader', 'soontirfel', 'fennrau', 'poedameron',
    'kyloren', 'majorvonreg', 'sunfac', 'dashrendar',
    'quickdraw', 'bountyrice', 'gideonhask', 'vedfoslo'
}

INITIATIVE_5_OR_HIGHER = INITIATIVE_6_PILOTS | {
    'lukeskywalker', 'whisper', 'bobafett', 'guri', 'anakinskywalker',
    'rey', 'ricolie', 'norrawexley', 'ketsuonyo', 'tomaxbren', 'sharabey'
}

BOMB_CARDS = {
    'protonbombs', 'seismiccharges', 'bombs', 'concussionbombs', 
    'clustermines', 'proximitymines', 'trajectorysimulator', 'electroprotonbomb'
}

TRACTOR_SHIPS = {
    'quadrijettransferspacetug', 'quadjumper', 'nantexclassstarfighter'
}

TRACTOR_PILOTS = {
    'ketsuonyo', 'unchakarhut', 'sarco-plank', 'constablezuvio', 'zuvio',
    'jakkuscavenger', 'guavianenforcer'
}

TRACTOR_CARDS = {
    'ensnare', 'tractorbeam', 'shadowcaster', 'tractorarray', 
    'spacetugtractorarray', 'pinpointtractorarray', 'tractor', 'tractortentacles', 'tractortechnicians'
}

HIGH_THREAT_JAM_CARDS = {
    'magpulsewarheads', 'sensorbuoysuite', 'enhancedjammingsuite',
    'sensorjammer', 'interferencearray', 'sensorscramblers', 'deadmansswitch'
}

JAM_CARDS = HIGH_THREAT_JAM_CARDS | {'jammingbeam'}

def analyze_rival_list(list_data: dict) -> dict:
    """
    Analiza a fondo la lista de un rival utilizando la base de datos canónica de X-Wing
    (resolución canónica directa por ID XWS oficial de YASB, iniciativas oficiales, agilidad, etc.).
    """
    lines = list_data.get('list_lines', [])
    raw_xws = list_data.get('raw_xws', '')
    
    num_ships = 0
    bomb_count = 0
    has_aces = False
    has_i6_aces = False
    has_i5_plus = False
    has_low_agility = False
    has_tractors = False
    has_small_ships = False
    has_large_ships = False
    has_jam = False
    has_high_init_jam = False
    jam_sources = []
    
    i6_count = 0
    i6_points = 0
    i5_count = 0
    i5_points = 0
    total_points = 0
    
    all_tokens = set()
    
    db = get_xwing_db()
    pilots_db = db.get('pilots', {})
    ships_db = db.get('ships', {})
    upgrades_db = db.get('upgrades', {})
    
    if raw_xws:
        try:
            data = json.loads(raw_xws)
            pilots = data.get('pilots', [])
            num_ships = len(pilots)
            total_points = data.get('points', 0)
            calc_points = 0
            
            for p in pilots:
                p_id = str(p.get('id', '')).lower().strip()
                p_name = str(p.get('name', '')).lower().strip()
                p_ship = str(p.get('ship', '')).lower().strip()
                p_pts = p.get('points', 0)
                calc_points += p_pts
                
                all_tokens.add(p_id)
                all_tokens.add(p_name)
                all_tokens.add(p_ship)
                
                # --- 1. Consulta canónica DIRECTA por ID único oficial XWS ---
                p_info = get_pilot_by_id(p_id, ship_hint=p_ship, name_hint=p_name, db=db)
                p_init = 0
                
                if p_info:
                    p_init = p_info.get('initiative', 0)
                    if not p_ship and p_info.get('ship'):
                        p_ship = p_info.get('ship')
                    if p_info.get('has_native_tractor'):
                        has_tractors = True
                else:
                    # Fallback heurístico solo si no está en la BD
                    if any(i6 in p_id for i6 in INITIATIVE_6_PILOTS):
                        p_init = 6
                    elif any(i5 in p_id for i5 in INITIATIVE_5_OR_HIGHER):
                        p_init = 5
                    if p_id in TRACTOR_PILOTS or 'ketsu' in p_id:
                        has_tractors = True

                if p_init == 6:
                    has_i6_aces = True
                    has_i5_plus = True
                    i6_count += 1
                    i6_points += p_pts
                elif p_init == 5:
                    has_i5_plus = True
                    i5_count += 1
                    i5_points += p_pts
                        
                if p_id in FRAGILE_ACES or p_name in FRAGILE_ACES:
                    has_aces = True

                # --- 2. Consulta canónica de la nave en la base de datos ---
                s_norm = p_ship.replace(' ', '').replace('-', '').replace("'", "")
                s_info = ships_db.get(s_norm) or ships_db.get(p_ship)
                
                is_high_init_boost = (p_id in HIGH_INIT_BOOST_LARGE_SHIPS or p_name in HIGH_INIT_BOOST_LARGE_SHIPS)
                
                if s_info:
                    agility = s_info.get('agility', 2)
                    size = str(s_info.get('size', '')).lower()
                    if agility <= 1 and not is_high_init_boost:
                        has_low_agility = True
                    if size in ('large', 'huge') or is_high_init_boost:
                        has_large_ships = True
                    elif size == 'small':
                        has_small_ships = True
                    if s_info.get('has_native_tractor'):
                        has_tractors = True
                else:
                    # Fallback heurístico de nave
                    if p_ship in LOW_AGILITY_SHIPS and not is_high_init_boost:
                        has_low_agility = True
                    if p_ship in LOW_AGILITY_SHIPS or is_high_init_boost:
                        has_large_ships = True
                    else:
                        has_small_ships = True
                    if p_ship in TRACTOR_SHIPS or any(ts in p_ship for ts in TRACTOR_SHIPS):
                        has_tractors = True

                # --- 3. Consulta canónica de mejoras en la base de datos ---
                upgrades = p.get('upgrades', {})
                if isinstance(upgrades, dict):
                    for cat, items in upgrades.items():
                        for item in items:
                            item_clean = str(item).lower()
                            all_tokens.add(item_clean)
                            
                            u_norm = item_clean.replace(' ', '').replace('-', '').replace("'", "")
                            u_info = upgrades_db.get(u_norm) or upgrades_db.get(item_clean)
                            
                            is_jam = False
                            if u_info:
                                if u_info.get('is_tractor'):
                                    has_tractors = True
                                if u_info.get('is_bomb'):
                                    bomb_count += 1
                                if u_norm in JAM_CARDS or item_clean in JAM_CARDS:
                                    is_jam = True
                            else:
                                if item_clean in BOMB_CARDS or 'bomb' in item_clean or 'mine' in item_clean or 'trajectory' in item_clean:
                                    bomb_count += 1
                                if item_clean in TRACTOR_CARDS or 'tractor' in item_clean or 'ensnare' in item_clean or 'shadowcaster' in item_clean:
                                    has_tractors = True
                                if item_clean in JAM_CARDS or any(j in item_clean for j in ('magpulse', 'enhancedjamming', 'jammingbeam', 'sensorbuoy', 'interferencearray')):
                                    is_jam = True
                                    
                            if is_jam:
                                has_jam = True
                                pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                                upgrade_label = u_info.get('name', item) if u_info else item
                                jam_sources.append(f"{upgrade_label} en {pilot_label} (I{p_init})")
                                is_high_threat = (u_norm in HIGH_THREAT_JAM_CARDS or item_clean in HIGH_THREAT_JAM_CARDS or any(j in item_clean for j in ('magpulse', 'enhancedjamming', 'sensorbuoy', 'interferencearray')))
                                if p_init >= 5 and is_high_threat:
                                    has_high_init_jam = True
                                    
            if total_points == 0:
                total_points = calc_points
                                
            obstacles = data.get('obstacles', [])
            for obs in obstacles:
                obs_str = str(obs).lower()
                all_tokens.add(obs_str)
                if 'bomb' in obs_str or 'mine' in obs_str:
                    bomb_count += 1
        except Exception:
            pass

    if num_ships == 0:
        for line in lines:
            line_str = str(line).strip()
            line_lower = line_str.lower()
            all_tokens.add(line_lower)
            
            # Reconocer formato numerado: ej. "1. Wedge Antilles (RZ-1 A-Wing) - 9 pts"
            m_pilot = re.match(r'^\d+\.\s*([^(]+?)(?:\s*\(([^)]+)\))?(?:\s*-\s*(\d+)\s*pts)?', line_str, re.IGNORECASE)
            if m_pilot:
                num_ships += 1
                p_text = m_pilot.group(1).strip()
                s_text = m_pilot.group(2).strip() if m_pilot.group(2) else ""
                p_pts = int(m_pilot.group(3)) if m_pilot.group(3) else 0
                total_points += p_pts
                
                p_info = get_pilot_by_id("", ship_hint=s_text, name_hint=p_text, db=db)
                p_init = 0
                if p_info:
                    p_init = p_info.get('initiative', 0)
                    if p_info.get('has_native_tractor'):
                        has_tractors = True
                        
                    s_canon = p_info.get('ship', '')
                    s_info = ships_db.get(s_canon)
                    if s_info:
                        agil = s_info.get('agility', 2)
                        sz = str(s_info.get('size', '')).lower()
                        if agil <= 1:
                            has_low_agility = True
                        if sz in ('large', 'huge'):
                            has_large_ships = True
                        elif sz == 'small':
                            has_small_ships = True
                else:
                    if any(ship in line_lower for ship in LOW_AGILITY_SHIPS):
                        if not any(hib in line_lower for hib in HIGH_INIT_BOOST_LARGE_SHIPS):
                            has_low_agility = True
                        has_large_ships = True
                        
                if p_init == 6:
                    has_i6_aces = True
                    has_i5_plus = True
                    i6_count += 1
                    i6_points += p_pts
                elif p_init == 5:
                    has_i5_plus = True
                    i5_count += 1
                    i5_points += p_pts

            if any(b in line_lower for b in BOMB_CARDS):
                bomb_count += 1
            if any(t in line_lower for t in TRACTOR_CARDS) or 'quadrijet' in line_lower or 'quadjumper' in line_lower or 'ketsu' in line_lower or 'ensnare' in line_lower:
                has_tractors = True
            if any(ace in line_lower for ace in FRAGILE_ACES):
                has_aces = True
            if any(j in line_lower for j in ('magpulse', 'enhanced jamming suite', 'jamming beam', 'sensor buoy', 'sensor jammer', 'interference array')):
                has_jam = True
                jam_sources.append(line_str)
                if any(hi in line_lower for hi in ('majorvonreg', 'kyloren', 'anakin', 'vader', 'fel', 'soontir')):
                    has_high_init_jam = True

    if num_ships >= 4:
        has_small_ships = True

    full_text = " ".join(lines).lower() + " " + raw_xws.lower()

    return {
        'num_ships': num_ships,
        'bomb_count': bomb_count,
        'has_aces': has_aces,
        'has_i6_aces': has_i6_aces,
        'has_i5_plus': has_i5_plus,
        'has_low_agility': has_low_agility,
        'has_tractors': has_tractors,
        'has_small_ships': has_small_ships,
        'has_large_ships': has_large_ships,
        'has_jam': has_jam,
        'has_high_init_jam': has_high_init_jam,
        'jam_sources': jam_sources,
        'i6_count': i6_count,
        'i6_points': i6_points,
        'i5_count': i5_count,
        'i5_points': i5_points,
        'i5_plus_count': i5_count + i6_count,
        'i5_plus_points': i5_points + i6_points,
        'total_points': total_points if total_points > 0 else 50,
        'tokens': all_tokens,
        'full_text': full_text
    }

def match_criterion(criterion: str, traits: dict) -> tuple[bool, str]:
    c = criterion.lower().strip()
    full_text = traits['full_text']
    tokens = traits['tokens']
    
    if c in ('iniciativa_alta', 'ases_i6', 'todos_seises', 'naves_i6', 'seises'):
        if traits.get('has_i6_aces'):
            return True, f"Ases de Iniciativa 6 en lista rival ({traits.get('i6_count', 1)} nave{'s' if traits.get('i6_count', 1) > 1 else ''}, {traits.get('i6_points', 0)} pts)"
        return False, ''
    if c in ('saturacion_i6', 'muro_i6', 'heavy_i6'):
        if traits.get('i6_count', 0) >= 2 or traits.get('i6_points', 0) >= 25:
            return True, f"Saturación de Iniciativa 6 ({traits.get('i6_count')} naves I6, {traits.get('i6_points')} pts)"
        return False, ''
    if c in ('magpulse', 'magpulsewarheads'):
        mag_sources = [s for s in traits.get('jam_sources', []) if 'magpulse' in s.lower()]
        if mag_sources or 'magpulse' in full_text:
            return True, f"Mag-Pulse Warheads en rival ({'; '.join(mag_sources) if mag_sources else 'Mag-Pulse Warheads'})"
        return False, ''
    if c in ('jam', 'interferencias', 'jamming'):
        if traits.get('has_high_init_jam'):
            sources_txt = "; ".join(traits.get('jam_sources', []))
            return True, f"Jamming a alta iniciativa I5-I6 ({sources_txt})"
        elif traits.get('has_jam'):
            sources_txt = "; ".join(traits.get('jam_sources', []))
            return True, f"Interferencias / Jam ({sources_txt})"
        return False, ''
    if c in ('iniciativa_baja', 'iniciativa_menor_5', 'sin_ases', 'menores_de_5'):
        if not traits.get('has_i5_plus') and traits.get('num_ships', 0) > 0:
            return True, 'Rival con todas las naves de iniciativa <= 4'
        return False, ''
    if c in ('bombas_masivas', 'bombas', 'muchas_bombas'):
        if traits['bomb_count'] >= 3:
            return True, f'Saturación de bombas ({traits["bomb_count"]} bombas/minas)'
        return False, ''
    if c == 'trajectorysimulator':
        if 'trajectorysimulator' in full_text:
            return True, 'Trajectory Simulator en lista rival'
        return False, ''
    if c in ('sin_bombas', 'cero_bombas'):
        if traits['bomb_count'] == 0:
            return True, 'Lista rival sin bombas/minas'
        return False, ''
    if c in ('enjambres', 'enjambre', 'enjambre_5+', 'enjambres_5+', 'enjambre_5'):
        if traits['num_ships'] >= 5:
            return True, f'Enjambre rival ({traits["num_ships"]} naves)'
        return False, ''
    if c in ('enjambre_6+', 'enjambres_6+', 'enjambre_6'):
        if traits['num_ships'] >= 6:
            return True, f'Enjambre puro ({traits["num_ships"]} naves)'
        return False, ''
    if c in ('pocas_naves', 'pocos_disparos'):
        if traits['num_ships'] <= 3 and traits['num_ships'] > 0:
            return True, f'Pocas naves ({traits["num_ships"]} naves)'
        return False, ''
    if c == 'ases_fragiles':
        if traits['has_aces']:
            return True, 'Ases frágiles detectados en rival'
        return False, ''
    if c in ('baja_agilidad', 'naves_lentas', 'poca_defensa', 'pocas_defensas', 'sin_defensa'):
        if traits['has_low_agility']:
            return True, 'Naves de baja agilidad / poca defensa'
        return False, ''
    if c in ('naves_grandes', 'naves_masa'):
        if traits['has_large_ships']:
            return True, 'Presencia de naves grandes'
        return False, ''
    if c == 'naves_pequenas':
        if traits['has_small_ships'] and not traits['has_large_ships']:
            return True, 'Lista completa de naves pequeñas'
        return False, ''
    if c == 'sin_grandes':
        if not traits['has_large_ships']:
            return True, 'Rival sin naves grandes'
        return False, ''
    if c == 'tractores':
        if traits['has_tractors']:
            return True, 'Tractores / Ensnare en rival'
        return False, ''
        
    # Coincidencia directa en tokens o texto
    if c in tokens or c in full_text:
        return True, f'Coincidencia con criterio "{c}"'
        
    return False, ''

def evaluate_player_vs_rival(player_profile: dict, rival_player_data: dict, traits: dict = None) -> dict:
    """
    Evalúa el emparejamiento entre la lista de un jugador y la del rival en un rango de 5 niveles:
      +2: Ideal / Muy Favorable (🟢🟢) - Gran sinergia positiva o hard counter a favor
      +1: Favorable (🟢) - Ventaja táctica moderada
       0: Igualado (🟡) - Enfrentamiento estándar / 50-50
      -1: Desfavorable (🟠) - Ligera desventaja táctica o incomodidad
      -2: Muy Desfavorable / Crítico (🔴🔴) - Trampa mortal o hard counter rival
    """
    if traits is None:
        traits = analyze_rival_list(rival_player_data)
        
    unfav_list = player_profile.get('unfavorable', [])
    fav_list = player_profile.get('favorable', [])
    hard_unfav_list = player_profile.get('hard_unfavorable', [])
    hard_fav_list = player_profile.get('hard_favorable', [])
    
    matched_favs = []
    reasons_fav = []
    matched_unfavs = []
    reasons_unfav = []
    
    # 1. Comprobar reglas desfavorables
    for unfav in unfav_list:
        matched, reason = match_criterion(unfav, traits)
        if matched:
            # Casos especiales de matiz (ej: tractores solo desfavorables si hay naves pequeñas)
            if unfav == 'tractores' and not traits['has_small_ships']:
                continue
            matched_unfavs.append(unfav)
            reasons_unfav.append(reason)
            
    # Hard counters desfavorables explícitos
    for h_unfav in hard_unfav_list:
        matched, reason = match_criterion(h_unfav, traits)
        if matched:
            matched_unfavs.append(h_unfav)
            matched_unfavs.append(h_unfav) # Doble peso
            reasons_unfav.append(f"[Hard Counter] {reason}")

    # 2. Comprobar reglas favorables
    for fav in fav_list:
        matched, reason = match_criterion(fav, traits)
        if matched:
            # Caso especial: pocas naves pero con bombas no es favorable si se busca sin_bombas
            if fav == 'pocas_naves' and traits['bomb_count'] > 0 and 'sin_bombas' in fav_list:
                continue
            matched_favs.append(fav)
            reasons_fav.append(reason)
            
    # Hard counters favorables explícitos
    for h_fav in hard_fav_list:
        matched, reason = match_criterion(h_fav, traits)
        if matched:
            matched_favs.append(h_fav)
            matched_favs.append(h_fav) # Doble peso
            reasons_fav.append(f"[Hard Counter] {reason}")

    # 3. Detección automática de intensidades extremas de X-Wing
    # Rival con 4+ bombas contra jugador sensible a bombas
    if ('bombas' in unfav_list or 'bombas_masivas' in unfav_list) and traits['bomb_count'] >= 4:
        if 'Saturación crítica de bombas' not in reasons_unfav:
            matched_unfavs.append('bombas_criticas')
            reasons_unfav.append(f"Saturación extrema ({traits['bomb_count']} bombas/minas)")

    # Rival con 7+ naves contra jugador que sufre contra enjambres
    if any(e in unfav_list for e in ('enjambres', 'enjambres_6+', 'enjambre_6+')) and traits['num_ships'] >= 7:
        if 'Enjambre masivo' not in reasons_unfav:
            matched_unfavs.append('enjambre_critico')
            reasons_unfav.append(f"Enjambre masivo ({traits['num_ships']} naves)")

    # Muro o saturación de Iniciativa 6 (2+ naves I6 o >= 25 pts en I6) contra jugador alérgico a I6
    if any(u in unfav_list for u in ('ases_i6', 'iniciativa_alta', 'seises', 'naves_i6')) and (traits['i6_count'] >= 2 or traits['i6_points'] >= 25):
        if 'saturacion_i6' not in matched_unfavs:
            matched_unfavs.append('saturacion_i6')
            reasons_unfav.append(f"Muro de Iniciativa 6 ({traits['i6_count']} naves I6, {traits['i6_points']} pts)")

    # Balance de puntuación
    fav_points = len(matched_favs)
    unfav_points = len(matched_unfavs)
    balance = fav_points - unfav_points
    
    if balance >= 2:
        score = 2
        symbol = '🟢🟢'
        reason = f"Ideal (+2): {'; '.join(reasons_fav)}"
        if reasons_unfav:
            reason += f" (Ojo con: {'; '.join(reasons_unfav)})"
    elif balance == 1:
        score = 1
        symbol = '🟢'
        reason = f"Favorable (+1): {'; '.join(reasons_fav)}"
        if reasons_unfav:
            reason += f" (Matiz rival: {'; '.join(reasons_unfav)})"
    elif balance == 0:
        score = 0
        symbol = '🟡'
        if reasons_fav and reasons_unfav:
            reason = f"Equilibrado (0): Pros ({'; '.join(reasons_fav)}) compensados por ({'; '.join(reasons_unfav)})"
        else:
            reason = "Igualado (Enfrentamiento estándar / 50-50)"
    elif balance == -1:
        score = -1
        symbol = '🟠'
        reason = f"Desfavorable (-1): {'; '.join(reasons_unfav)}"
        if reasons_fav:
            reason += f" (A favor: {'; '.join(reasons_fav)})"
    else: # balance <= -2
        score = -2
        symbol = '🔴🔴'
        reason = f"Crítico (-2): {'; '.join(reasons_unfav)}"
        if reasons_fav:
            reason += f" (Aunque favorable en: {'; '.join(reasons_fav)})"

    return {'score': score, 'symbol': symbol, 'reason': reason}

def evaluate_matchup_matrix(profiles_data: dict, rival_players: list) -> dict:
    players = profiles_data.get('players', [])
    matrix = {}
    player_net_scores = {}
    player_defensive_scores = {}
    
    rival_traits_map = {
        p.get('player_name', f'Rival {i+1}'): analyze_rival_list(p)
        for i, p in enumerate(rival_players)
    }
    
    for p_prof in players:
        p_name = p_prof.get('alias') or p_prof.get('player_name')
        matrix[p_name] = {}
        net = 0
        p2_count = 0
        p1_count = 0
        c0_count = 0
        m1_count = 0
        m2_count = 0
        
        for r_data in rival_players:
            r_name = r_data.get('player_name', 'Rival')
            traits = rival_traits_map[r_name]
            res = evaluate_player_vs_rival(p_prof, r_data, traits)
            matrix[p_name][r_name] = res
            
            score = res['score']
            net += score
            if score == 2:
                p2_count += 1
            elif score == 1:
                p1_count += 1
            elif score == 0:
                c0_count += 1
            elif score == -1:
                m1_count += 1
            elif score == -2:
                m2_count += 1
                
        player_net_scores[p_name] = net
        # Puntuación defensiva WTC para Escudos:
        # Penalización extrema para -2 (-6), penalización moderada para -1 (-2),
        # premia solidez de 0 (+1), bonificación moderada de +1 (+2) y +2 (+3).
        player_defensive_scores[p_name] = (
            (m2_count * -6) + (m1_count * -2) + (c0_count * 1) + (p1_count * 2) + (p2_count * 3)
        )
        
    return {
        'matrix': matrix,
        'net_scores': player_net_scores,
        'defensive_scores': player_defensive_scores,
        'rival_traits': rival_traits_map
    }

def determine_roles_for_rival_team(profiles_data: dict, rival_players: list) -> dict:
    """
    Calcula dinámicamente qué jugadores deben ser Escudos y Lanzas frente a ESTE equipo rival concreto,
    basándose exclusivamente en la matriz NxN de 5 niveles (-2 a +2):
      1. Menor cantidad de cruces muy desfavorables (🔴🔴 / -2): Cero tolerancia a trampas mortales a ciegas.
      2. Menor cantidad de cruces desfavorables (🟠 / -1).
      3. Menor cantidad de cruces ideales (🟢🟢 / +2): Reservar a los especialistas arrolladores para LANZAS ofensivas.
      4. Mayor cantidad de cruces neutros (🟡 / 0): Máxima consistencia y solidez defensiva 50-50.
      5. Mayor puntuación defensiva neta ponderada.
    """
    eval_res = evaluate_matchup_matrix(profiles_data, rival_players)
    matrix = eval_res['matrix']
    net_scores = eval_res['net_scores']
    defensive_scores = eval_res['defensive_scores']
    
    players = profiles_data.get('players', [])
    team_size = len(players)
    num_shields = profiles_data.get('num_shields', (team_size - 1) // 2)
    num_spears = profiles_data.get('num_spears', (team_size + 1) // 2)
    
    player_ranks = []
    for p in players:
        name = p.get('alias') or p.get('player_name')
        m2_count = sum(1 for r_res in matrix[name].values() if r_res['score'] == -2)
        m1_count = sum(1 for r_res in matrix[name].values() if r_res['score'] == -1)
        c0_count = sum(1 for r_res in matrix[name].values() if r_res['score'] == 0)
        p1_count = sum(1 for r_res in matrix[name].values() if r_res['score'] == 1)
        p2_count = sum(1 for r_res in matrix[name].values() if r_res['score'] == 2)
        
        player_ranks.append({
            'profile': p,
            'name': name,
            'm2': m2_count,
            'm1': m1_count,
            'c0': c0_count,
            'p1': p1_count,
            'p2': p2_count,
            'net_score': net_scores[name],
            'defensive_score': defensive_scores[name]
        })
        
    # Ordenación para ESCUDOS:
    # 1. Menos -2 (evitar peligro crítico)
    # 2. Menos -1 (minimizar desventajas leves)
    # 3. Menos +2 (reservar a las lanzas los emparejamientos letales)
    # 4. Más 0 (máxima roca 50-50)
    # 5. Mayor score defensivo ponderado
    player_ranks.sort(key=lambda x: (x['m2'], x['m1'], x['p2'], -x['c0'], -x['defensive_score']))
    
    shields = player_ranks[:num_shields]
    spears = player_ranks[num_shields:]
    
    # Asignar roles finales para este rival
    shields_names = [s['name'] for s in shields]
    spears_names = [sp['name'] for sp in spears]
    
    # Calcular sacrificio WTC para las lanzas contra cada defensor rival
    rival_best_spears_map = {}
    for r_data in rival_players:
        r_name = r_data.get('player_name', 'Rival')
        candidates = []
        for sp_name in spears_names:
            spec_score = matrix[sp_name][r_name]['score']
            glob_score = net_scores[sp_name]
            candidates.append((sp_name, spec_score, glob_score))
            
        # Criterio WTC: Mayor spec_score DESC (+2 antes que +1), menor glob_score ASC (sacrificar al de menor valor global)
        candidates.sort(key=lambda x: (x[1], -x[2]), reverse=True)
        top2 = sorted([candidates[0][0], candidates[1][0]]) if len(candidates) >= 2 else [candidates[0][0]]
        rival_best_spears_map[r_name] = top2
        
    return {
        'matrix': matrix,
        'net_scores': net_scores,
        'defensive_scores': defensive_scores,
        'shields': shields,
        'spears': spears,
        'shields_names': shields_names,
        'spears_names': spears_names,
        'rival_best_spears_map': rival_best_spears_map
    }
