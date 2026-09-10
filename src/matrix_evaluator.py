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

HEAVY_ORDNANCE_CARDS = {
    'plasmatorpedoes', 'protontorpedoes', 'advprotontorpedoes', 'advancedprotontorpedoes',
    'iontorpedoes', 'homingmissiles', 'concussionmissiles', 'clustermissiles',
    'diamondboronmissiles', 'barragerockets', 'ionmissiles', 'protonrockets'
}

DOUBLE_ARC_3_DICE_SHIPS = {
    'firespray31starfighter', 'firespray31',
    'modifiedyt1300lightfreighter', 'scavengedyt1300', 'customizedyt1300lightfreighter',
    'yt1300', 'yt1300lightfreighter',
    'lancerclasspursuitcraft',
    'gauntletfighter'
}

ION_CARDS = {
    'ionbombs', 'iontorpedoes', 'ionmissiles', 'ioncannon',
    'ioncannonturret', 'connernet', 'connernets', 'pulsedrayshield', 'precisionionengines'
}

STRESS_CONTROL_CARDS = {
    '000', 'triplezero', 'rebelcaptive', 'thermaldetonators',
    'tacticalscrambler', 'r4b11', 'captainphasma', 'phasma',
    'r3a2', 'stressbot', 'flechettetorpedoes', 'flechettecannon'
}

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
    has_medium_ships = False
    has_large_ships = False
    all_small_ships = True
    has_jam = False
    has_high_init_jam = False
    jam_sources = []
    
    has_ordnance = False
    ordnance_count = 0
    ordnance_sources = []
    
    has_double_arc_3_dice = False
    double_arc_sources = []
    
    low_hp_count = 0
    low_hp_points = 0
    low_hp_ships = []
    
    has_ions = False
    ion_sources = []
    has_stress_control = False
    stress_sources = []
    has_high_init_ordnance = False
    high_init_ordnance_sources = []
    
    has_force = False
    force_count = 0
    force_sources = []
    
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
                
                ship_hp = 0
                if s_info:
                    agility = s_info.get('agility', 2)
                    size = str(s_info.get('size', '')).lower()
                    if agility <= 1 and not is_high_init_boost:
                        has_low_agility = True
                    is_large_canonical = any(l in s_norm for l in ('yt1300', 'decimator', 'vcx100', 'lancer', 'ghost', 'falcon', 'houndstooth', 'yv666'))
                    is_medium_canonical = any(m in s_norm for m in ('firespray', 'arc170', 'reaper', 'st70', 'gauntlet', 'xiclass', 'uwing', 'btlbywing', 'laat'))
                    if size in ('large', 'huge') or is_high_init_boost or is_large_canonical:
                        has_large_ships = True
                        all_small_ships = False
                    elif size == 'medium' or is_medium_canonical:
                        has_medium_ships = True
                        all_small_ships = False
                    elif size == 'small':
                        has_small_ships = True
                    if s_info.get('has_native_tractor'):
                        has_tractors = True
                    ship_hp = s_info.get('hull', 0) + s_info.get('shields', 0)
                else:
                    # Fallback heurístico de nave
                    if p_ship in LOW_AGILITY_SHIPS and not is_high_init_boost:
                        has_low_agility = True
                    if p_ship in LOW_AGILITY_SHIPS or is_high_init_boost:
                        has_large_ships = True
                        all_small_ships = False
                    elif any(med in p_ship for med in ('firespray', 'arc170', 'reaper', 'st70', 'gauntlet', 'xiclass', 'xi-class')):
                        has_medium_ships = True
                        all_small_ships = False
                    else:
                        has_small_ships = True
                    if p_ship in TRACTOR_SHIPS or any(ts in p_ship for ts in TRACTOR_SHIPS):
                        has_tractors = True
                    if any(frag in p_ship for frag in ('tieln', 'tieba', 'tiein', 'awing', 'vwing', 'trifighter', 'vulture', 'z95', 'fang', 'm3a', 'actis')):
                        ship_hp = 3

                if 0 < ship_hp <= 4:
                    low_hp_count += 1
                    low_hp_points += p_pts
                    pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                    low_hp_ships.append(f"{pilot_label} ({ship_hp} HP)")

                is_double_arc_3 = False
                if s_norm in DOUBLE_ARC_3_DICE_SHIPS or p_ship in DOUBLE_ARC_3_DICE_SHIPS or any(d in p_ship for d in ('firespray', 'yt1300', 'lancerclass', 'gauntlet')):
                    is_double_arc_3 = True
                    has_double_arc_3_dice = True
                    pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                    ship_label = s_info.get('name', p_ship) if s_info else p_ship
                    double_arc_sources.append(f"{ship_label} ({pilot_label})")

                # --- 2.5 Detección de usuarios de la Fuerza / Ases Jedi ---
                is_force = False
                p_check = (p_id + " " + p_name + " " + p_ship).lower()
                if any(f in p_check for f in ('jedi', 'delta7', 'eta2', 'actis', 'anakin', 'obiwan', 'plokoon', 'adigallia', 'vader', 'luke', 'yoda', 'inquisitor', 'ahsoka', 'mace', 'saesee', 'luminara', 'barriss', 'asajj', 'ezra', 'kanan', 'kylo')):
                    is_force = True

                # --- 3. Consulta canónica de mejoras en la base de datos ---
                upgrades = p.get('upgrades', {})
                if isinstance(upgrades, dict):
                    for cat, items in upgrades.items():
                        if 'force' in cat.lower():
                            is_force = True
                        for item in items:
                            item_clean = str(item).lower()
                            all_tokens.add(item_clean)
                            
                            u_norm = item_clean.replace(' ', '').replace('-', '').replace("'", "")
                            u_info = upgrades_db.get(u_norm) or upgrades_db.get(item_clean)
                            
                            is_jam = False
                            is_ordnance = False
                            if u_info:
                                if u_info.get('is_tractor'):
                                    has_tractors = True
                                if u_info.get('is_bomb'):
                                    bomb_count += 1
                                if u_norm in JAM_CARDS or item_clean in JAM_CARDS:
                                    is_jam = True
                                is_control_missile = ('magpulse' in u_norm or 'magpulse' in item_clean or 'energyshell' in u_norm or 'energyshell' in item_clean)
                                if not is_control_missile and (u_info.get('is_torpedo') or u_info.get('is_missile') or u_norm in HEAVY_ORDNANCE_CARDS or item_clean in HEAVY_ORDNANCE_CARDS):
                                    is_ordnance = True
                            else:
                                if item_clean in BOMB_CARDS or 'bomb' in item_clean or 'mine' in item_clean or 'trajectory' in item_clean:
                                    bomb_count += 1
                                if item_clean in TRACTOR_CARDS or 'tractor' in item_clean or 'ensnare' in item_clean or 'shadowcaster' in item_clean:
                                    has_tractors = True
                                if item_clean in JAM_CARDS or any(j in item_clean for j in ('magpulse', 'enhancedjamming', 'jammingbeam', 'sensorbuoy', 'interferencearray')):
                                    is_jam = True
                                is_control_missile = ('magpulse' in item_clean or 'energyshell' in item_clean)
                                if not is_control_missile and (item_clean in HEAVY_ORDNANCE_CARDS or any(o in item_clean for o in ('torpedo', 'plasma', 'concussion', 'homing', 'protonrocket'))):
                                    is_ordnance = True
                                    
                            if is_ordnance:
                                has_ordnance = True
                                ordnance_count += 1
                                pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                                upgrade_label = u_info.get('name', item) if u_info else item
                                ordnance_sources.append(f"{upgrade_label} en {pilot_label}")
                                if p_init >= 5:
                                    has_high_init_ordnance = True
                                    high_init_ordnance_sources.append(f"{upgrade_label} en {pilot_label} (I{p_init})")

                            is_ion = False
                            ion_pattern = r'\bion(?:cannon|torpedo|missile|bomb|turret|beam|s)?\b|precisionion'
                            if u_norm in ION_CARDS or item_clean in ION_CARDS or re.search(ion_pattern, item_clean):
                                is_ion = True
                            if is_ion:
                                has_ions = True
                                pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                                upgrade_label = u_info.get('name', item) if u_info else item
                                ion_sources.append(f"{upgrade_label} en {pilot_label}")

                            is_stress = False
                            if u_norm in STRESS_CONTROL_CARDS or item_clean in STRESS_CONTROL_CARDS or any(st in item_clean for st in ('thermal', '000', 'rebelcaptive')):
                                is_stress = True
                            if is_stress:
                                has_stress_control = True
                                pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                                upgrade_label = u_info.get('name', item) if u_info else item
                                stress_sources.append(f"{upgrade_label} en {pilot_label}")

                            if is_jam:
                                has_jam = True
                                pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                                upgrade_label = u_info.get('name', item) if u_info else item
                                jam_sources.append(f"{upgrade_label} en {pilot_label} (I{p_init})")
                                is_high_threat = (u_norm in HIGH_THREAT_JAM_CARDS or item_clean in HIGH_THREAT_JAM_CARDS or any(j in item_clean for j in ('magpulse', 'enhancedjamming', 'sensorbuoy', 'interferencearray')))
                                if p_init >= 5 and is_high_threat:
                                    has_high_init_jam = True
                                    
                if is_force:
                    has_force = True
                    force_count += 1
                    pilot_label = p_info.get('name', p_name or p_id) if p_info else (p_name or p_id)
                    force_sources.append(pilot_label)
                                    
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
                            all_small_ships = False
                        elif sz == 'medium':
                            has_medium_ships = True
                            all_small_ships = False
                        elif sz == 'small':
                            has_small_ships = True
                        shp = s_info.get('hull', 0) + s_info.get('shields', 0)
                        if 0 < shp <= 4:
                            low_hp_count += 1
                            low_hp_points += p_pts
                            low_hp_ships.append(f"{p_text} ({shp} HP)")
                else:
                    if any(ship in line_lower for ship in LOW_AGILITY_SHIPS):
                        if not any(hib in line_lower for hib in HIGH_INIT_BOOST_LARGE_SHIPS):
                            has_low_agility = True
                        has_large_ships = True
                        all_small_ships = False
                        
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
            if any(d in line_lower for d in ('firespray', 'yt-1300', 'yt1300', 'halcon', 'falcon', 'lancer', 'gauntlet')):
                has_double_arc_3_dice = True
                double_arc_sources.append(line_str)
            if re.search(r'\bion(?:cannon|torpedo|missile|bomb|turret|beam|s)?\b|precisionion', line_lower):
                has_ions = True
                ion_sources.append(line_str)
            if any(s in line_lower for s in ('0-0-0', 'triple zero', 'thermal detonator', 'rebel captive', 'phasma', 'captainphasma', 'captain phasma', 'r3-a2', 'stressbot', 'flechette')):
                has_stress_control = True
                stress_sources.append(line_str)
            if any(o in line_lower for o in ('torpedo', 'plasma', 'concussion', 'homing', 'proton rocket', 'adv. proton')) and 'magpulse' not in line_lower:
                has_ordnance = True
                ordnance_sources.append(line_str)
                if p_init >= 5:
                    has_high_init_ordnance = True
                    high_init_ordnance_sources.append(f"{line_str} (I{p_init})")

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
        'has_medium_ships': has_medium_ships,
        'has_large_ships': has_large_ships,
        'all_small_ships': all_small_ships,
        'has_jam': has_jam,
        'has_high_init_jam': has_high_init_jam,
        'jam_sources': jam_sources,
        'has_ordnance': has_ordnance,
        'ordnance_count': ordnance_count,
        'ordnance_sources': ordnance_sources,
        'has_double_arc_3_dice': has_double_arc_3_dice,
        'double_arc_sources': double_arc_sources,
        'low_hp_count': low_hp_count,
        'low_hp_points': low_hp_points,
        'low_hp_ships': low_hp_ships,
        'has_ions': has_ions,
        'ion_sources': ion_sources,
        'has_stress_control': has_stress_control,
        'stress_sources': stress_sources,
        'has_high_init_ordnance': has_high_init_ordnance,
        'high_init_ordnance_sources': high_init_ordnance_sources,
        'has_force': has_force,
        'force_count': force_count,
        'force_sources': force_sources,
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
    if c in ('naves_pequenas', 'todo_pequenas'):
        if traits.get('has_small_ships') and traits.get('all_small_ships'):
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
    if c in ('muchas_iniciativas_altas', 'iniciativas_altas', 'iniciativas_5_6', 'multiples_iniciativas_altas'):
        i5_plus_count = traits.get('i5_plus_count', 0)
        i5_plus_points = traits.get('i5_plus_points', 0)
        i6_count = traits.get('i6_count', 0)
        if i5_plus_count >= 3 or (i5_plus_count >= 2 and i5_plus_points >= 28) or i6_count >= 2:
            return True, f"Múltiples iniciativas altas I5-I6 ({i5_plus_count} naves I5+, {i5_plus_points} pts)"
        return False, ''
    if c in ('armamento_secundario', 'torpedos_misiles', 'plasmas_torpedos', 'plasmas', 'torpedos', 'ordnance', 'armamento_pesado'):
        if traits.get('has_ordnance'):
            sources_txt = "; ".join(traits.get('ordnance_sources', []))
            return True, f"Armamento secundario pesado ({sources_txt})"
        return False, ''
    if c in ('doble_arco_3_dados', 'doble_arco_3', 'doble_arco', 'torreta_pesada', 'torretas_pesadas', 'firespray_halcon', 'firesprays_halcones'):
        if traits.get('has_double_arc_3_dice'):
            sources_txt = "; ".join(traits.get('double_arc_sources', []))
            return True, f"Naves de doble arco / 3 dados ({sources_txt})"
        return False, ''
    if c in ('poca_vida', 'naves_poca_vida', 'baja_vida', 'vida_baja', 'naves_fragiles_vida'):
        count = traits.get('low_hp_count', 0)
        pts = traits.get('low_hp_points', 0)
        total_pts = traits.get('total_points', 50)
        pct = (pts / total_pts * 100) if total_pts > 0 else 0
        if count >= 2 and (pts >= 18 or pct >= 35.0):
            ships_summary = "; ".join(traits.get('low_hp_ships', []))
            return True, f"Naves de poca vida (<=4 HP) por saturación ({count} naves, {pts} pts [{pct:.0f}%]: {ships_summary})"
        return False, ''
    if c in ('alpha_strike', 'alpha_strike_i5_i6', 'ordnance_i5_i6'):
        if traits.get('has_high_init_ordnance'):
            sources_txt = "; ".join(traits.get('high_init_ordnance_sources', []))
            return True, f"Alpha Strike I5-I6 con armamento pesado ({sources_txt})"
        return False, ''
    if c in ('muchos_seises', 'saturacion_i6', 'muro_i6', 'heavy_i6'):
        if traits.get('i6_count', 0) >= 2 or traits.get('i6_points', 0) >= 20:
            return True, f"Múltiples iniciativas 6 ({traits.get('i6_count')} naves I6, {traits.get('i6_points')} pts)"
        return False, ''
    if c in ('control_estres', 'estres', 'pone_estres'):
        if traits.get('has_stress_control'):
            sources_txt = "; ".join(traits.get('stress_sources', []))
            return True, f"Control de estrés en rival ({sources_txt})"
        return False, ''
    if c in ('iones', 'armas_iones', 'ion'):
        if traits.get('has_ions'):
            sources_txt = "; ".join(traits.get('ion_sources', []))
            return True, f"Armamento de iones ({sources_txt})"
        return False, ''
    if c in ('escuadron_4_5', '4_5_naves', 'semienjambre', 'semienjambres'):
        if traits.get('num_ships', 0) in (4, 5) and not traits.get('has_large_ships'):
            return True, f"Semienjambre favorable ({traits.get('num_ships')} naves)"
        return False, ''
    if c in ('fuerza', 'ases_fuerza', 'fuerza_movilidad', 'pilotos_fuerza', 'fuerza_esquiva'):
        if traits.get('force_count', 0) >= 2:
            sources_txt = "; ".join(traits.get('force_sources', []))
            return True, f"Ases de la Fuerza con alta movilidad y esquiva ({traits.get('force_count')} pilotos: {sources_txt})"
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
        
    unfav_list = list(player_profile.get('unfavorable', []))
    fav_list = list(player_profile.get('favorable', []))
    hard_unfav_list = list(player_profile.get('hard_unfavorable', []))
    hard_fav_list = list(player_profile.get('hard_favorable', []))
    vulns = player_profile.get('vulnerabilities', {})
    
    matched_favs = []
    reasons_fav = []
    matched_unfavs = []
    reasons_unfav = []
    
    # 0. Evaluación de los 5 Checks Comunes de Vulnerabilidad (bombas, estrés, iones, jam, tractores)
    if vulns:
        common_check_tags = {
            'bombas': {'bombas', 'bombas_masivas', 'muchas_bombas', 'trajectorysimulator'},
            'estres': {'control_estres', 'estres', 'pone_estres'},
            'iones': {'iones', 'armas_iones', 'ion'},
            'jam': {'jam', 'interferencias', 'jamming', 'magpulse', 'magpulsewarheads'},
            'tractores': {'tractores', 'tractor'}
        }
        tags_to_filter = set()
        for tag_set in common_check_tags.values():
            tags_to_filter.update(tag_set)
        unfav_list = [u for u in unfav_list if u.lower().strip() not in tags_to_filter]

        if vulns.get('bombas'):
            if traits.get('bomb_count', 0) >= 2 or 'trajectorysimulator' in traits.get('full_text', ''):
                cnt = traits.get('bomb_count', 0)
                if cnt >= 4:
                    matched_unfavs.append(2.0)
                    reasons_unfav.append(f"Saturación crítica de bombas ({cnt} bombas/minas)")
                else:
                    matched_unfavs.append(1.0)
                    reasons_unfav.append(f"Vulnerable a bombas ({cnt} bombas/minas)")

        if vulns.get('estres'):
            if traits.get('has_stress_control'):
                sources_txt = "; ".join(traits.get('stress_sources', []))
                matched_unfavs.append(1.0)
                reasons_unfav.append(f"Vulnerable a control de estrés ({sources_txt})")

        if vulns.get('iones'):
            if traits.get('has_ions'):
                sources_txt = "; ".join(traits.get('ion_sources', []))
                matched_unfavs.append(0.5)
                reasons_unfav.append(f"Vulnerable a armamento de iones ({sources_txt})")

        if vulns.get('jam'):
            if traits.get('has_high_init_jam'):
                sources_txt = "; ".join(traits.get('jam_sources', []))
                matched_unfavs.append(1.0)
                reasons_unfav.append(f"Vulnerable a Jamming a alta iniciativa ({sources_txt})")
            elif traits.get('has_jam'):
                sources_txt = "; ".join(traits.get('jam_sources', []))
                matched_unfavs.append(1.0)
                reasons_unfav.append(f"Vulnerable a Jamming ({sources_txt})")

        if vulns.get('tractores'):
            if traits.get('has_tractors'):
                matched_unfavs.append(1.0)
                reasons_unfav.append("Vulnerable a Haces Tractores / Ensnare")

    # 1. Comprobar reglas desfavorables
    for unfav in unfav_list:
        matched, reason = match_criterion(unfav, traits)
        if matched:
            weight = 0.5 if unfav in ('iones', 'armas_iones', 'ion') else 1.0
            matched_unfavs.append(weight)
            reasons_unfav.append(f"{reason} (penalización leve 0.5)" if weight == 0.5 else reason)
            
    # Hard counters desfavorables explícitos
    for h_unfav in hard_unfav_list:
        matched, reason = match_criterion(h_unfav, traits)
        if matched:
            matched_unfavs.append(2.0) # Doble peso
            reasons_unfav.append(f"[Hard Counter] {reason}")

    # 2. Comprobar reglas favorables
    for fav in fav_list:
        matched, reason = match_criterion(fav, traits)
        if matched:
            # Caso especial: pocas naves pero con bombas no es favorable si se busca sin_bombas
            if fav == 'pocas_naves' and traits['bomb_count'] > 0 and 'sin_bombas' in fav_list:
                continue
            matched_favs.append(1.0)
            reasons_fav.append(reason)
            
    # Hard counters favorables explícitos
    for h_fav in hard_fav_list:
        matched, reason = match_criterion(h_fav, traits)
        if matched:
            matched_favs.append(2.0) # Doble peso
            reasons_fav.append(f"[Hard Counter] {reason}")

    # 3. Detección automática de intensidades extremas de X-Wing
    # Rival con 4+ bombas contra jugador sensible a bombas
    bomb_sensitive = vulns.get('bombas') if vulns else ('bombas' in unfav_list or 'bombas_masivas' in unfav_list)
    if bomb_sensitive and traits['bomb_count'] >= 4:
        if not any('bombas' in r.lower() for r in reasons_unfav):
            matched_unfavs.append(1.0)
            reasons_unfav.append(f"Saturación extrema ({traits['bomb_count']} bombas/minas)")

    # Rival con 7+ naves contra jugador que sufre contra enjambres
    if any(e in unfav_list for e in ('enjambres', 'enjambres_6+', 'enjambre_6+')) and traits['num_ships'] >= 7:
        if 'Enjambre masivo' not in reasons_unfav:
            matched_unfavs.append(1.0)
            reasons_unfav.append(f"Enjambre masivo ({traits['num_ships']} naves)")

    # Muro o saturación de Iniciativa 6 (2+ naves I6 o >= 25 pts en I6) contra jugador alérgico a I6
    if any(u in unfav_list for u in ('ases_i6', 'iniciativa_alta', 'seises', 'naves_i6', 'muchos_seises')) and (traits['i6_count'] >= 2 or traits['i6_points'] >= 25):
        if 'saturacion_i6' not in matched_unfavs:
            matched_unfavs.append(1.0)
            reasons_unfav.append(f"Muro de Iniciativa 6 ({traits['i6_count']} naves I6, {traits['i6_points']} pts)")

    # Balance de puntuación
    fav_points = sum(matched_favs)
    unfav_points = sum(matched_unfavs)
    balance = fav_points - unfav_points
    
    if balance >= 1.5:
        score = 2
        symbol = '🟢🟢'
        reason = f"Ideal (+2): {'; '.join(reasons_fav)}"
        if reasons_unfav:
            reason += f" (Ojo con: {'; '.join(reasons_unfav)})"
    elif balance >= 0.5:
        score = 1
        symbol = '🟢'
        reason = f"Favorable (+1): {'; '.join(reasons_fav)}"
        if reasons_unfav:
            reason += f" (Matiz rival: {'; '.join(reasons_unfav)})"
    elif balance >= -0.5:
        score = 0
        symbol = '🟡'
        if reasons_fav and reasons_unfav:
            reason = f"Equilibrado (0): Pros ({'; '.join(reasons_fav)}) compensados por ({'; '.join(reasons_unfav)})"
        elif reasons_unfav:
            reason = f"Equilibrado (0): Amenaza leve ({'; '.join(reasons_unfav)})"
        else:
            reason = "Igualado (Enfrentamiento estándar / 50-50)"
    elif balance > -1.5:
        score = -1
        symbol = '🟠'
        reason = f"Desfavorable (-1): {'; '.join(reasons_unfav)}"
        if reasons_fav:
            reason += f" (A favor: {'; '.join(reasons_fav)})"
    else: # balance <= -1.5
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
