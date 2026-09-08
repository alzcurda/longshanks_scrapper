import re
import json

LOW_AGILITY_SHIPS = {
    'yt1300', 'customizedyt1300lightfreighter', 'vcx100lightfreighter', 
    'vt49decimator', 'btlbywing', 'ywing', 'ywing-swz82', 'laatigunship',
    'lambdaclasst4ashuttle', 'upsilonclassshuttle', 'gr75mediumtransport'
}

HIGH_INIT_BOOST_LARGE_SHIPS = {
    'hansolo', 'bobafett', 'dashrendar', 'lando-calrissian', 'rey'
}

FRAGILE_ACES = {
    'soontirfel', 'whisper', 'bobafett', 'guri', 'fennrau', 'wedgeantilles',
    'poedameron', 'kylo-ren', 'anakinskywalker'
}

BOMB_CARDS = {
    'protonbombs', 'seismiccharges', 'bombs', 'concussionbombs', 
    'clustermines', 'proximitymines', 'trajectorysimulator', 'electroprotonbomb'
}

TRACTOR_CARDS = {
    'ensnare', 'tractorbeam', 'shadowcaster', 'tractorarray', 'tractor'
}

def analyze_rival_list(list_data: dict) -> dict:
    """
    Analiza a fondo la lista de un rival a partir de su XWS o líneas parseadas.
    """
    lines = list_data.get('list_lines', [])
    raw_xws = list_data.get('raw_xws', '')
    
    num_ships = 0
    bomb_count = 0
    has_aces = False
    has_low_agility = False
    has_tractors = False
    has_small_ships = False
    has_large_ships = False
    all_tokens = set()
    
    if raw_xws:
        try:
            data = json.loads(raw_xws)
            pilots = data.get('pilots', [])
            num_ships = len(pilots)
            
            for p in pilots:
                p_id = str(p.get('id', '')).lower()
                p_name = str(p.get('name', '')).lower()
                p_ship = str(p.get('ship', '')).lower()
                all_tokens.add(p_id)
                all_tokens.add(p_name)
                all_tokens.add(p_ship)
                
                if p_id in FRAGILE_ACES or p_name in FRAGILE_ACES:
                    has_aces = True
                    
                is_high_init_boost = (p_id in HIGH_INIT_BOOST_LARGE_SHIPS or p_name in HIGH_INIT_BOOST_LARGE_SHIPS)
                if p_ship in LOW_AGILITY_SHIPS and not is_high_init_boost:
                    has_low_agility = True
                if p_ship in LOW_AGILITY_SHIPS or is_high_init_boost:
                    has_large_ships = True
                else:
                    has_small_ships = True
                    
                upgrades = p.get('upgrades', {})
                if isinstance(upgrades, dict):
                    for cat, items in upgrades.items():
                        for item in items:
                            item_clean = str(item).lower()
                            all_tokens.add(item_clean)
                            if item_clean in BOMB_CARDS or 'bomb' in item_clean or 'mine' in item_clean or 'trajectory' in item_clean:
                                bomb_count += 1
                            if item_clean in TRACTOR_CARDS or 'tractor' in item_clean or 'ensnare' in item_clean:
                                has_tractors = True
                                
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
            line_str = str(line).lower()
            all_tokens.add(line_str)
            if re.match(r'^\d+\.', line_str.strip()):
                num_ships += 1
            if any(b in line_str for b in BOMB_CARDS):
                bomb_count += 1
            if any(t in line_str for t in TRACTOR_CARDS):
                has_tractors = True
            if any(ace in line_str for ace in FRAGILE_ACES):
                has_aces = True
            if any(ship in line_str for ship in LOW_AGILITY_SHIPS):
                if not any(hib in line_str for hib in HIGH_INIT_BOOST_LARGE_SHIPS):
                    has_low_agility = True
                has_large_ships = True

    if num_ships >= 4:
        has_small_ships = True

    full_text = " ".join(lines).lower() + " " + raw_xws.lower()

    return {
        'num_ships': num_ships,
        'bomb_count': bomb_count,
        'has_aces': has_aces,
        'has_low_agility': has_low_agility,
        'has_tractors': has_tractors,
        'has_small_ships': has_small_ships,
        'has_large_ships': has_large_ships,
        'tokens': all_tokens,
        'full_text': full_text
    }

def match_criterion(criterion: str, traits: dict) -> tuple[bool, str]:
    c = criterion.lower().strip()
    full_text = traits['full_text']
    tokens = traits['tokens']
    
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
    if c in ('enjambre_5+', 'enjambres_5+', 'enjambre_5'):
        if traits['num_ships'] >= 5:
            return True, f'Enjambre de saturación ({traits["num_ships"]} naves)'
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
    if c in ('baja_agilidad', 'naves_lentas'):
        if traits['has_low_agility']:
            return True, 'Naves de baja agilidad / cargueros lentos'
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
    if traits is None:
        traits = analyze_rival_list(rival_player_data)
        
    unfav_list = player_profile.get('unfavorable', [])
    fav_list = player_profile.get('favorable', [])
    
    # 1. Comprobar reglas desfavorables
    for unfav in unfav_list:
        matched, reason = match_criterion(unfav, traits)
        if matched:
            # Casos especiales de matiz (ej: tractores solo desfavorables si hay naves pequeñas)
            if unfav == 'tractores' and not traits['has_small_ships']:
                continue
            return {'score': -1, 'symbol': '🔴', 'reason': f'Desfavorable: {reason}'}
            
    # 2. Comprobar reglas favorables
    for fav in fav_list:
        matched, reason = match_criterion(fav, traits)
        if matched:
            # Caso especial: Alzu pocas naves pero si hay bombas no es favorable
            if fav == 'pocas_naves' and traits['bomb_count'] > 0 and 'sin_bombas' in fav_list:
                continue
            return {'score': 1, 'symbol': '🟢', 'reason': f'Favorable: {reason}'}
            
    # 3. Neutro por defecto
    return {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento estándar / 50-50)'}

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
        greens = 0
        yellows = 0
        reds = 0
        
        for r_data in rival_players:
            r_name = r_data.get('player_name', 'Rival')
            traits = rival_traits_map[r_name]
            res = evaluate_player_vs_rival(p_prof, r_data, traits)
            matrix[p_name][r_name] = res
            
            score = res['score']
            net += score
            if score > 0:
                greens += 1
            elif score < 0:
                reds += 1
            else:
                yellows += 1
                
        player_net_scores[p_name] = net
        # Puntuación defensiva: penaliza severamente los rojos (-3), premia amarillos (+1) y verdes (+2)
        player_defensive_scores[p_name] = (reds * -3) + (yellows * 1) + (greens * 2)
        
    return {
        'matrix': matrix,
        'net_scores': player_net_scores,
        'defensive_scores': player_defensive_scores,
        'rival_traits': rival_traits_map
    }

def determine_roles_for_rival_team(profiles_data: dict, rival_players: list) -> dict:
    """
    Calcula dinámicamente qué jugadores deben ser Escudos y Lanzas frente a ESTE equipo rival concreto.
    """
    eval_res = evaluate_matchup_matrix(profiles_data, rival_players)
    matrix = eval_res['matrix']
    net_scores = eval_res['net_scores']
    defensive_scores = eval_res['defensive_scores']
    
    players = profiles_data.get('players', [])
    team_size = len(players)
    num_shields = profiles_data.get('num_shields', (team_size - 1) // 2)
    num_spears = profiles_data.get('num_spears', (team_size + 1) // 2)
    
    affinity_weights = {'muy alta': 3, 'alta': 2, 'media': 1, 'baja': 0}
    
    player_ranks = []
    for p in players:
        name = p.get('alias') or p.get('player_name')
        d_score = defensive_scores[name]
        red_count = sum(1 for r_res in matrix[name].values() if r_res['score'] < 0)
        aff = affinity_weights.get(p.get('defensive_affinity', 'media'), 1)
        # Ordenación: Menos rojos (prioridad máxima), mayor defensive_score, mayor afinidad defensiva
        player_ranks.append({
            'profile': p,
            'name': name,
            'reds': red_count,
            'defensive_score': d_score,
            'net_score': net_scores[name],
            'affinity': aff
        })
        
    player_ranks.sort(key=lambda x: (x['reds'], -x['defensive_score'], -x['affinity']))
    
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
            
        # Criterio WTC: Mayor spec_score DESC, menor glob_score ASC (sacrificar al de menos verdes globales)
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
