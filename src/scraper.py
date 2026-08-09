import re
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import BASE_URL, DEFAULT_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT, MAX_PARALLEL_WORKERS
from src.parser import parse_player_pop_info, clean_text
from src.storage import save_event_data

def get_event_teams_and_players(event_id: str) -> dict:
    """
    Obtiene la lista de equipos y sus participantes para un torneo en Longshanks.
    """
    url = f"{BASE_URL}/events/detail/panel_standings.php?event={event_id}&section=team"
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    teams = []
    seen_team_names = set()
    
    team_blocks = soup.find_all('div', class_=lambda c: c and 'player' in c and 'team' in c)
    if not team_blocks:
        team_blocks = soup.find_all('div', class_=lambda c: c and 'player' in c)
        
    for block in team_blocks:
        team_link = block.find('a', onclick=lambda o: o and 'pop_team' in o)
        if not team_link:
            continue
            
        team_name = clean_text(team_link.get_text())
        if not team_name or team_name in seen_team_names:
            continue
            
        seen_team_names.add(team_name)
        
        team_id = ""
        onclick_team = team_link.get('onclick', '')
        team_id_match = re.search(r'pop_team\((\d+)\)', onclick_team)
        if team_id_match:
            team_id = team_id_match.group(1)
            
        players = []
        seen_player_ids = set()
        
        player_links = block.find_all('a', onclick=lambda o: o and 'pop_user' in o)
        for p_link in player_links:
            p_name = clean_text(p_link.get_text())
            onclick_user = p_link.get('onclick', '')
            p_id_match = re.search(r'pop_user\((\d+)', onclick_user)
            
            if p_id_match:
                p_id = p_id_match.group(1)
                if p_id not in seen_player_ids and p_name:
                    seen_player_ids.add(p_id)
                    players.append({
                        'player_id': p_id,
                        'player_name': p_name
                    })
                    
        teams.append({
            'team_id': team_id,
            'team_name': team_name,
            'players': players
        })
        
    return {
        'event_id': str(event_id),
        'teams': teams
    }

def fetch_single_player_data(args) -> tuple:
    """Descarga de forma segura los datos de un participante."""
    player_id, event_id, player_name, team_name = args
    url = f"{BASE_URL}/admin/players/pop_info.php?player={player_id}&event={event_id}"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY)
        
        parsed = parse_player_pop_info(response.text)
        parsed['player_id'] = str(player_id)
        parsed['player_name'] = player_name
        parsed['team_name'] = team_name
        return (team_name, player_id, parsed)
    except Exception as e:
        print(f"   [!] Error al descargar {player_name} (#{player_id}): {e}", flush=True)
        return (team_name, player_id, {
            'player_id': str(player_id),
            'player_name': player_name,
            'team_name': team_name,
            'faction': 'Desconocida',
            'points': '0 pts',
            'list_lines': [f"Error de descarga: {e}"]
        })

def download_and_save_event(event_id: str) -> dict:
    """
    Descarga todo el torneo desde Longshanks (equipos + listas en paralelo)
    y lo guarda en un archivo JSON local (data/event_<event_id>.json).
    """
    print(f"[*] Obteniendo lista de equipos para el evento #{event_id}...", flush=True)
    event_info = get_event_teams_and_players(event_id)
    teams = event_info.get('teams', [])
    
    tasks = []
    for team in teams:
        t_name = team.get('team_name', 'Equipo')
        for p in team.get('players', []):
            p_id = p.get('player_id')
            p_name = p.get('player_name')
            tasks.append((p_id, event_id, p_name, t_name))

    total = len(tasks)
    print(f"[+] Se encontraron {len(teams)} equipos con {total} participantes.", flush=True)
    print(f"[*] Descargando listas en paralelo ({MAX_PARALLEL_WORKERS} hilos)...", flush=True)
    
    player_map = {}
    completed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        futures = {executor.submit(fetch_single_player_data, task): task for task in tasks}
        for future in as_completed(futures):
            completed += 1
            t_name, p_id, p_data = future.result()
            player_map[(t_name, p_id)] = p_data
            if completed % 10 == 0 or completed == total:
                print(f"   Progreso: [{completed}/{total}] listas descargadas...", flush=True)

    # Organizar participantes descargados en sus correspondientes equipos
    for team in teams:
        t_name = team.get('team_name', 'Equipo')
        team['players_data'] = []
        for p in team.get('players', []):
            p_id = p.get('player_id')
            p_data = player_map.get((t_name, p_id))
            if p_data:
                team['players_data'].append(p_data)

    # Guardar en almacenamiento local
    save_event_data(event_id, event_info)
    return event_info
