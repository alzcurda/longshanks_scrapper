import json
import re
from bs4 import BeautifulSoup

def clean_text(text: str) -> str:
    """Limpia espacios en blanco y caracteres nulos."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def clean_id(val: str) -> str:
    """Convierte IDs formateados en nombres legibles con mayúsculas y espacios."""
    if not val:
        return ""
    val = str(val).replace('-', ' ').strip()
    return val.title()

def parse_xws_json(raw_json_str: str) -> list[str]:
    """
    Parsea un string JSON en formato XWS (estándar de X-Wing 2.0 / 2.5)
    y lo convierte en líneas de texto formateadas.
    """
    lines = []
    try:
        data = json.loads(raw_json_str)
        faction_raw = data.get('faction', '')
        faction_map = {
            'galacticrepublic': 'Galactic Republic',
            'galacticempire': 'Galactic Empire',
            'rebelalliance': 'Rebel Alliance',
            'separatistalliance': 'Separatist Alliance',
            'firstorder': 'First Order',
            'resistance': 'Resistance',
            'scumandvillainy': 'Scum & Villainy'
        }
        faction = faction_map.get(faction_raw, clean_id(faction_raw))
        
        name = data.get('name', '')
        points = data.get('points', '')
        
        if name:
            lines.append(f"Nombre Lista: {name}")
        if points:
            lines.append(f"Puntos: {points}")
        if faction:
            lines.append(f"Facción: {faction}")
        
        lines.append("")
        lines.append("PILOTOS Y MEJORAS:")
        
        pilots = data.get('pilots', [])
        for i, p in enumerate(pilots, 1):
            p_name = clean_id(p.get('name', p.get('id', 'Desconocido')))
            p_pts = p.get('points', '')
            p_ship = clean_id(p.get('ship', ''))
            
            header_str = f"{i}. {p_name}"
            if p_ship:
                header_str += f" ({p_ship})"
            if p_pts:
                header_str += f" - {p_pts} pts"
            lines.append(header_str)
            
            upgrades = p.get('upgrades', {})
            if isinstance(upgrades, dict):
                for category, up_list in upgrades.items():
                    for item in up_list:
                        lines.append(f"   • [{clean_id(category)}] {clean_id(item)}")
            lines.append("")
            
        obstacles = data.get('obstacles', [])
        if obstacles:
            lines.append("OBSTÁCULOS:")
            for obs in obstacles:
                lines.append(f" • {clean_id(obs)}")
                
    except Exception as e:
        lines.append(f"(Error parseando XWS: {e})")
    
    return lines

def parse_player_pop_info(html_content: str) -> dict:
    """
    Parsea la respuesta HTML de pop_info.php de un jugador.
    Extrae: player_name, team_name, faction, points, xws_data y list_lines.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Buscar la etiqueta <textarea id="list_XXXX"> donde Longshanks guarda el JSON XWS original
    raw_xws = None
    textarea = soup.find('textarea', id=re.compile(r'^list_\d+'))
    if not textarea:
        textarea = soup.find('textarea')
        
    if textarea and textarea.get_text().strip().startswith('{'):
        raw_xws = textarea.get_text().strip()

    # 2. Extraer información general del jugador del HTML
    player_name = ""
    team_name = ""
    faction = ""
    points = ""
    
    # Buscar el nombre del jugador (ej: <h2>-Azriel-</h2> o encabezado)
    for tag in soup.find_all(['h2', 'h3', 'h1', 'div']):
        text = clean_text(tag.get_text())
        if tag.name in ['h1', 'h2', 'h3'] and text and 'Longshanks' not in text:
            player_name = text
            break
            
    text_content = soup.get_text()
    
    # Extraer equipo
    team_match = re.search(r'Team\s*\n?\s*([^\n]+)', text_content)
    if team_match:
        team_name = clean_text(team_match.group(1))
        
    # Extraer facción
    faction_match = re.search(r'Faction\s*\n?\s*([^\n]+)', text_content)
    if faction_match:
        faction = clean_text(faction_match.group(1))
        
    # Extraer puntos
    pts_match = re.search(r'(\d+)\s*points', text_content, re.IGNORECASE)
    if pts_match:
        points = pts_match.group(1) + " pts"
        
    # Construir líneas de la lista
    list_lines = []
    
    if raw_xws:
        list_lines = parse_xws_json(raw_xws)
    else:
        # Extraer líneas de texto de la lista a partir del HTML como alternativa
        in_pilots = False
        for elem in soup.find_all(['div', 'p', 'li', 'span', 'h4', 'h5']):
            txt = clean_text(elem.get_text())
            if not txt:
                continue
            if 'Pilots' in txt or 'points' in txt:
                in_pilots = True
            if in_pilots and len(txt) > 2:
                if txt not in list_lines and not any(ignored in txt for ignored in ['General information', 'LSID', 'Rating', 'Awards']):
                    list_lines.append(txt)
                    
    return {
        'player_name': player_name,
        'team_name': team_name,
        'faction': faction,
        'points': points,
        'raw_xws': raw_xws,
        'list_lines': list_lines
    }
