import os
import json
import gspread
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials

from src.config import BASE_DIR
from src.matrix_evaluator import evaluate_5x5_matrix

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

CREDENTIALS_SA_PATH = os.path.join(BASE_DIR, "credentials.json")
CREDENTIALS_OAUTH_PATH = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

def get_gspread_client():
    if os.path.exists(CREDENTIALS_SA_PATH):
        creds = Credentials.from_service_account_file(CREDENTIALS_SA_PATH, scopes=SCOPES)
        return gspread.authorize(creds)

    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = UserCredentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_OAUTH_PATH):
                raise FileNotFoundError(
                    "No se encontraron credenciales de Google.\n"
                    f"Coloca 'client_secret.json' en la carpeta: {BASE_DIR}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_OAUTH_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return gspread.authorize(creds)

def build_nested_if_formula_tanda1(drop_cell_ref: str, rival_best_map: dict) -> str:
    items = list(rival_best_map.items())
    if not items:
        return '"No disponible"'
        
    formula = f'"⚔️ {items[-1][1]}"'
    for r_nick, best_atks in reversed(items[:-1]):
        formula = f'IF({drop_cell_ref}="{r_nick}", "⚔️ {best_atks}", {formula})'
        
    return "=" + formula

def export_to_gsheet(event_id: str, event_data: dict) -> str:
    """
    Crea DIRECTAMENTE un nuevo Google Sheet online en Google Drive
    con Matriz 5x5, Asistente Bidireccional WTC y Listas completas.
    """
    client = get_gspread_client()
    
    sheet_title = f"Longshanks Event #{event_id} - Listas por Equipos"
    print(f"[*] Creando Google Sheet online directamente: '{sheet_title}'...", flush=True)
    
    sh = client.create(sheet_title)
    
    # -------------------------------------------------------------
    # Pestaña 1: Resumen Torneo
    # -------------------------------------------------------------
    ws_summary = sh.sheet1
    ws_summary.update_title("Resumen Torneo")
    
    summary_rows = [
        [f"Longshanks Event #{event_id} - Resumen por Equipos"],
        [],
        ["Equipo", "ID Jugador", "Jugador / Nick", "Facción", "Puntos"]
    ]
    
    for team in event_data.get('teams', []):
        t_name = team.get('team_name', 'Desconocido')
        for p in team.get('players_data', []):
            summary_rows.append([
                t_name,
                p.get('player_id', ''),
                p.get('player_name', ''),
                p.get('faction', ''),
                p.get('points', '')
            ])
            
    ws_summary.update(range_name="A1", values=summary_rows)
    
    # -------------------------------------------------------------
    # Pestañas por Cada Equipo
    # -------------------------------------------------------------
    teams = event_data.get('teams', [])
    mudhorns_info = [
        ("Alzu", "Rebeldes (Defensor #1 Fijo)"),
        ("Ander", "Separatistas (Defensor #2 Fijo)"),
        ("Marc", "Primera Orden (Lanza)"),
        ("Koli", "República (Lanza)"),
        ("Ale", "Scum (Lanza)")
    ]
    lanzas_list = ["Marc", "Koli", "Ale"]

    for team in teams:
        t_name = team.get('team_name', 'Equipo')[:31]
        players_data = team.get('players_data', [])
        
        ws_team = sh.add_worksheet(title=t_name, rows=35, cols=max(len(players_data), 8))
        
        matrix_headers = ["Jugador Mudhorn", "Perfil / Rol"]
        rival_nicks = []
        rival_best_tanda1 = {}

        for p_data in players_data:
            r_nick = p_data.get('player_name', 'Rival')
            rival_nicks.append(r_nick)
            matrix_headers.append(f"vs {r_nick}")
            
            eval_matrix = evaluate_5x5_matrix(p_data)
            
            lanzas1 = []
            for m_name in lanzas_list:
                lanzas1.append((m_name, eval_matrix.get(m_name, {}).get('score', 0)))
            lanzas1.sort(key=lambda x: -x[1])
            rival_best_tanda1[r_nick] = f"{lanzas1[0][0]} y {lanzas1[1][0]}"

        matrix_headers.append("Balance Net Score")
        
        matrix_rows = [
            [f"Equipo Rival: {t_name}"],
            [],
            ["🎯 MATRIZ DE EMPAREJAMIENTOS 5x5 (Iberian Mudhorns vs Rival)"],
            matrix_headers
        ]
        
        for m_name, m_role in mudhorns_info:
            row_eval = [m_name, m_role]
            net_score = 0
            for p_data in players_data:
                eval_matrix = evaluate_5x5_matrix(p_data)
                res = eval_matrix.get(m_name, {'score': 0, 'symbol': '🟡'})
                score = res['score']
                symbol = res['symbol']
                net_score += score
                row_eval.append(f"{symbol} ({score:+d})")
                
            row_eval.append(f"{net_score:+d}")
            matrix_rows.append(row_eval)
            
        formula1 = build_nested_if_formula_tanda1("C14", rival_best_tanda1)
        formula2 = '=IF(C16="Marc", "⚔️ Koli y Ale", IF(C16="Koli", "⚔️ Marc y Ale", "⚔️ Marc y Koli"))'

        matrix_rows.append([])
        matrix_rows.append(["🎛️ ASISTENTE BIDIRECCIONAL DE PAIRING (PANEL CONTROL WTC TIEMPO REAL)"])
        matrix_rows.append(["🔵 TANDA 1 (Primeros 2 Emparejamientos)"])
        matrix_rows.append(["[OFERTA 1A] Su Defensor -> Nuestras Lanzas", "", "", "", "[OFERTA 1B] Nuestro Defensor #1 Alzu -> Sus Atacantes"])
        matrix_rows.append(["1️⃣ Defensor Rival #1 revelado:", "", rival_nicks[0] if rival_nicks else "", "", "• Atacante Rival #1A para Alzu:", "", rival_nicks[1] if len(rival_nicks)>1 else ""])
        matrix_rows.append(["💡 Nuestras 2 Lanzas recomendadas:", "", formula1, "", "• Atacante Rival #1B para Alzu:", "", rival_nicks[2] if len(rival_nicks)>2 else ""])
        matrix_rows.append(["2️⃣ ¿Qué Lanza aceptó el rival?:", "", "Marc", "", "💡 Recomendación para Alzu:", "", '=IF(G14="", "Esperando asignación", "🛡️ Recomendado: " & G14)'])
        matrix_rows.append(["", "", "", "", "3️⃣ Atacante Rival aceptado para Alzu (Cruce 2):", "", rival_nicks[1] if len(rival_nicks)>1 else ""])
        
        matrix_rows.append([])
        matrix_rows.append(["🔴 TANDA 2 (Emparejamientos 3, 4 y 5)"])
        matrix_rows.append(["[OFERTA 2A] Su Defensor #2 -> Lanzas Restantes", "", "", "", "[OFERTA 2B] Nuestro Defensor #2 Ander -> Sus Atacantes"])
        matrix_rows.append(["4️⃣ Defensor Rival #2 revelado:", "", rival_nicks[3] if len(rival_nicks)>3 else "", "", "• Atacante Rival #2A para Ander:", "", rival_nicks[3] if len(rival_nicks)>3 else ""])
        matrix_rows.append(["💡 Lanzas disponibles en Tanda 2:", "", formula2, "", "• Atacante Rival #2B para Ander:", "", rival_nicks[4] if len(rival_nicks)>4 else ""])
        matrix_rows.append(["5️⃣ ¿Qué Lanza aceptó el rival?:", "", "Koli", "", "💡 Recomendación para Ander:", "", '=IF(G21="", "Esperando asignación", "🛡️ Recomendado: " & G21)'])
        matrix_rows.append(["", "", "", "", "6️⃣ Atacante Rival aceptado para Ander (Cruce 4):", "", rival_nicks[3] if len(rival_nicks)>3 else ""])
        
        matrix_rows.append(["⚡ Cruce 5 (Automático por descarte final):", "", '=IF(AND(C16<>"Marc", C23<>"Marc"), "⚔️ Marc", IF(AND(C16<>"Koli", C23<>"Koli"), "⚔️ Koli", "⚔️ Ale"))'])
        
        matrix_rows.append([])
        matrix_rows.append(["📋 LISTAS COMPLETAS DE INTEGRANTES DEL EQUIPO RIVAL"])
        
        row_nicks = []
        row_factions = []
        row_points = []
        row_lists = []
        
        for p_data in players_data:
            row_nicks.append(p_data.get('player_name', 'Jugador'))
            row_factions.append(f"Facción: {p_data.get('faction', '')}")
            row_points.append(f"Total: {p_data.get('points', '')}")
            
            lines = p_data.get('list_lines', [])
            full_text = "\n".join(lines) if lines else "Sin lista registrada"
            row_lists.append(full_text)
            
        matrix_rows.append(row_nicks)
        matrix_rows.append(row_factions)
        matrix_rows.append(row_points)
        matrix_rows.append(row_lists)
        
        ws_team.update(range_name="A1", values=matrix_rows)

    try:
        sh.share(None, perm_type='anyone', role='reader')
    except Exception:
        pass
        
    url = sh.url
    print(f"\n[SUCCESS] Google Sheet creado con Asistente Bidireccional WTC!")
    print(f"🔗 Enlace directo: {url}", flush=True)
    return url
