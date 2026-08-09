import re

# Definición de heurísticas de naves y cartas para X-Wing
LOW_AGILITY_SHIPS = {
    'yt1300', 'customizedyt1300lightfreighter', 'vcx100lightfreighter', 
    'vt49decimator', 'btlbywing', 'ywing', 'ywing-swz82', 'laatigunship',
    'lambdaclasst4ashuttle', 'upsilonclassshuttle', 'gr75mediumtransport'
}

FRAGILE_ACES = {
    'soontirfel', 'whisper', 'bobafett', 'guri', 'fennrau', 'wedgeantilles',
    'poedameron', 'kylo-ren', 'anakinskywalker'
}

BOMB_CARDS = {
    'protonbombs', 'seismiccharges', 'bombs', 'concussionbombs', 
    'clustermines', 'proximitymines', 'trajectorysimulator', 'electroprotonbomb'
}

def analyze_rival_list(list_data: dict) -> dict:
    """
    Analiza la lista de un rival a partir de sus datos parseados o JSON XWS.
    Devuelve características clave: num_ships, bomb_count, has_aces, has_low_agility.
    """
    lines = list_data.get('list_lines', [])
    raw_xws = list_data.get('raw_xws', '')
    
    num_ships = 0
    bomb_count = 0
    has_aces = False
    has_low_agility = False
    
    if raw_xws:
        try:
            import json
            data = json.loads(raw_xws)
            pilots = data.get('pilots', [])
            num_ships = len(pilots)
            
            for p in pilots:
                p_id = str(p.get('id', '')).lower()
                p_name = str(p.get('name', '')).lower()
                p_ship = str(p.get('ship', '')).lower()
                
                if p_id in FRAGILE_ACES or p_name in FRAGILE_ACES:
                    has_aces = True
                if p_ship in LOW_AGILITY_SHIPS:
                    has_low_agility = True
                    
                upgrades = p.get('upgrades', {})
                if isinstance(upgrades, dict):
                    for cat, items in upgrades.items():
                        for item in items:
                            item_clean = str(item).lower()
                            if item_clean in BOMB_CARDS or 'bomb' in item_clean or 'mine' in item_clean or 'trajectory' in item_clean:
                                bomb_count += 1
                                
            obstacles = data.get('obstacles', [])
            for obs in obstacles:
                if 'bomb' in str(obs).lower() or 'mine' in str(obs).lower():
                    bomb_count += 1
                    
        except Exception:
            pass

    if num_ships == 0:
        for line in lines:
            line_str = str(line).lower()
            if re.match(r'^\d+\.', line_str.strip()):
                num_ships += 1
            if any(b in line_str for b in BOMB_CARDS):
                bomb_count += 1
            if any(ace in line_str for ace in FRAGILE_ACES):
                has_aces = True
            if any(ship in line_str for ship in LOW_AGILITY_SHIPS):
                has_low_agility = True

    return {
        'num_ships': num_ships,
        'bomb_count': bomb_count,
        'has_aces': has_aces,
        'has_low_agility': has_low_agility
    }

def evaluate_5x5_matrix(rival_player_data: dict) -> dict:
    """
    Evalúa las 5 comparativas del equipo Iberian Mudhorns contra 1 participante rival.
    """
    traits = analyze_rival_list(rival_player_data)
    num_ships = traits['num_ships']
    bomb_count = traits['bomb_count']
    has_aces = traits['has_aces']
    has_low_agility = traits['has_low_agility']
    
    matrix = {}
    
    # 1. Alzu (Rebeldes - Tanque de Resistencia)
    if bomb_count >= 3 or 'trajectorysimulator' in str(rival_player_data).lower():
        matrix['Alzu'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs saturación masiva de bombas/minas.'}
    elif num_ships <= 3 and bomb_count == 0:
        matrix['Alzu'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable vs pocos disparos pesados sin bombas.'}
    else:
        matrix['Alzu'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento neutro/estándar).'}
        
    # 2. Ale (Scum - 3 Naves Grandes)
    if bomb_count >= 3:
        matrix['Ale'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs bombas de área y control de zona.'}
    elif has_low_agility or num_ships <= 3:
        matrix['Ale'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable vs naves de baja agilidad o masa.'}
    else:
        matrix['Ale'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento estándar).'}

    # 3. Ander (Separatistas - Firesprays + Sun Fac)
    if has_low_agility or num_ships <= 3:
        matrix['Ander'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable vs naves lentas o agrupadas (Sun Fac).'}
    else:
        matrix['Ander'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Matchup 50/50 neutro).'}

    # 4. Koli (República - Ases de Fuerza)
    if num_ships >= 5:
        matrix['Koli'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs enjambres de saturación (5+ naves).'}
    elif has_aces or has_low_agility or num_ships <= 3:
        matrix['Koli'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable vs Ases frágiles o cargueros lentos.'}
    else:
        matrix['Koli'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento estándar).'}

    # 5. Marc (Primera Orden - Kylo + Midnight)
    if num_ships >= 6:
        matrix['Marc'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs enjambres puros (6+ naves baratas).'}
    elif has_aces or has_low_agility or num_ships <= 4:
        matrix['Marc'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable (Midnight anula modificaciones defensivas).'}
    else:
        matrix['Marc'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento estándar).'}

    return matrix

def get_team_pairing_recommendations(rival_players_data: list) -> dict:
    """
    Calcula la estrategia de emparejamientos recomendada contra un equipo rival:
    - 2 Defensores (Escudos): Menos rojos (🔴), menor riesgo para enviar a ciegas.
    - 3 Atacantes (Lanzas): Mayor potencial ofensivo (🟢) contra listas específicas.
    """
    mudhorns_players = ["Alzu", "Ale", "Ander", "Koli", "Marc"]
    player_scores = {m: {'net': 0, 'reds': 0, 'greens': 0, 'yellows': 0} for m in mudhorns_players}
    
    for p_data in rival_players_data:
        eval_matrix = evaluate_5x5_matrix(p_data)
        for m_name in mudhorns_players:
            score = eval_matrix.get(m_name, {}).get('score', 0)
            player_scores[m_name]['net'] += score
            if score > 0:
                player_scores[m_name]['greens'] += 1
            elif score < 0:
                player_scores[m_name]['reds'] += 1
            else:
                player_scores[m_name]['yellows'] += 1

    # Ordenar por menor cantidad de rojos primero, luego mayor net score (Defensores idealmente 0 rojos)
    sorted_for_defense = sorted(
        mudhorns_players,
        key=lambda m: (player_scores[m]['reds'], -player_scores[m]['net'], -player_scores[m]['yellows'])
    )
    
    defender_1 = sorted_for_defense[0]
    defender_2 = sorted_for_defense[1]
    attackers = sorted_for_defense[2:]
    
    # Garantizar que Alzu sea considerado Defensor Principal si tiene 0 rojos
    if 'Alzu' in mudhorns_players and player_scores['Alzu']['reds'] == 0:
        if defender_1 != 'Alzu':
            defender_2 = defender_1
            defender_1 = 'Alzu'
            attackers = [m for m in mudhorns_players if m not in (defender_1, defender_2)]

    return {
        'defender_1': defender_1,
        'defender_2': defender_2,
        'attackers': attackers,
        'stats': player_scores
    }
