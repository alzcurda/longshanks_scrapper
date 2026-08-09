import re

# Definición de heurísticas de naves y cartas para X-Wing
LOW_AGILITY_SHIPS = {
    'yt1300', 'customizedyt1300lightfreighter', 'vcx100lightfreighter', 
    'vt49decimator', 'btlbywing', 'ywing', 'ywing-swz82', 'laatigunship',
    'lambdaclasst4ashuttle', 'upsilonclassshuttle', 'gr75mediumtransport'
}

# Pilotos/Naves grandes con Alta Iniciativa (5-6) e Impulso (Boost) que NO deben considerarse lentas
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
    'ensnare', 'tractorbeam', 'shadowcaster', 'tractorArray', 'tractor'
}

def analyze_rival_list(list_data: dict) -> dict:
    """
    Analiza la lista de un rival a partir de sus datos parseados o JSON XWS.
    Aplica las reglas avanzadas de agilidad/iniciativa y haces tractores.
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
                    
                # Regla 1: Si es nave grande pero con Iniciativa alta (5-6) e Impulso (Boost), NO es lenta
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
                            if item_clean in BOMB_CARDS or 'bomb' in item_clean or 'mine' in item_clean or 'trajectory' in item_clean:
                                bomb_count += 1
                            if item_clean in TRACTOR_CARDS or 'tractor' in item_clean or 'ensnare' in item_clean:
                                has_tractors = True
                                
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

    return {
        'num_ships': num_ships,
        'bomb_count': bomb_count,
        'has_aces': has_aces,
        'has_low_agility': has_low_agility,
        'has_tractors': has_tractors,
        'has_small_ships': has_small_ships,
        'has_large_ships': has_large_ships
    }

def evaluate_5x5_matrix(rival_player_data: dict) -> dict:
    """
    Evalúa las 5 comparativas del equipo Iberian Mudhorns contra 1 participante rival
    aplicando las reglas avanzadas de agilidad/impulso y tractores.
    """
    traits = analyze_rival_list(rival_player_data)
    num_ships = traits['num_ships']
    bomb_count = traits['bomb_count']
    has_aces = traits['has_aces']
    has_low_agility = traits['has_low_agility']
    has_tractors = traits['has_tractors']
    has_small_ships = traits['has_small_ships']
    has_large_ships = traits['has_large_ships']
    
    matrix = {}
    
    # 1. Alzu (Rebeldes - Tanque de Resistencia)
    if bomb_count >= 3 or 'trajectorysimulator' in str(rival_player_data).lower():
        matrix['Alzu'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs saturación masiva de bombas/minas.'}
    elif num_ships <= 3 and bomb_count == 0:
        matrix['Alzu'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable vs pocos disparos pesados sin bombas.'}
    else:
        matrix['Alzu'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento neutro/estándar).'}
        
    # 2. Ander (Separatistas - Sun Fac con Ensnare/Tractores)
    # Regla 2: Tractores son muy eficaces contra naves pequeñas, pero ineficientes contra medianas/grandes
    if has_small_ships and not has_large_ships:
        matrix['Ander'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable (Tractores/Ensnare devastadores vs naves pequeñas).'}
    elif has_large_ships:
        matrix['Ander'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Tractores poco eficientes vs naves medianas/grandes).'}
    else:
        matrix['Ander'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Matchup 50/50 neutro).'}

    # 3. Marc (Primera Orden - Kylo + Midnight)
    if num_ships >= 6:
        matrix['Marc'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs enjambres puros (6+ naves baratas).'}
    elif has_tractors and has_small_ships:
        matrix['Marc'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs tractores rivales que fijan naves pequeñas.'}
    elif has_aces or has_low_agility or num_ships <= 4:
        matrix['Marc'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable (Midnight anula modificaciones defensivas).'}
    else:
        matrix['Marc'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento estándar).'}

    # 4. Koli (República - Ases Delta-7 de Fuerza)
    if num_ships >= 5:
        matrix['Koli'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs enjambres de saturación (5+ naves).'}
    elif has_tractors and has_small_ships:
        matrix['Koli'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs tractores rivales eficaces vs naves pequeñas.'}
    elif has_aces or has_low_agility or num_ships <= 3:
        matrix['Koli'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable vs Ases frágiles o cargueros lentos sin agilidad.'}
    else:
        matrix['Koli'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento estándar).'}

    # 5. Ale (Scum - 3 Naves Grandes / Masa / Han Solo)
    # Regla 2: Tractores rivales son ineficientes contra las naves grandes de Ale
    if bomb_count >= 3:
        matrix['Ale'] = {'score': -1, 'symbol': '🔴', 'reason': 'Desfavorable vs bombas de área y control de zona.'}
    elif has_tractors:
        matrix['Ale'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable (Tractores rivales ineficientes vs naves grandes de Ale).'}
    elif has_low_agility or num_ships <= 3:
        matrix['Ale'] = {'score': 1, 'symbol': '🟢', 'reason': 'Favorable vs naves de baja agilidad o masa.'}
    else:
        matrix['Ale'] = {'score': 0, 'symbol': '🟡', 'reason': 'Igualado (Enfrentamiento estándar).'}

    return matrix
