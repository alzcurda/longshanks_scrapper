import os
import json
import gspread
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials

from src.config import BASE_DIR
from src.team_manager import (
    load_or_create_profiles, get_or_set_team_config, calculate_roles_distribution
)
from src.matrix_evaluator import determine_roles_for_rival_team

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

CREDENTIALS_SA_PATH = os.path.join(BASE_DIR, "credentials.json")
CREDENTIALS_OAUTH_PATH = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

STEP_EMOJIS = {
    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
}

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

def build_spears_formula(def_cell_ref: str, rival_best_spears_map: dict) -> str:
    items = list(rival_best_spears_map.items())
    if not items:
        return '"No disponible"'
    
    formula = f'"⚔️ {" y ".join(items[-1][1])}"'
    for r_nick, best_sps in reversed(items[:-1]):
        val = " y ".join(best_sps)
        formula = f'IF({def_cell_ref}="{r_nick}", "⚔️ {val}", {formula})'
    return "=" + formula

def build_shield_rec_formula(sh_name: str, c_atk1_ref: str, c_atk2_ref: str, sh_eval_map: dict, rival_nicks: list) -> str:
    if not rival_nicks:
        return f'=IF({c_atk1_ref}="", "Esperando asignación", "🛡️ " & {c_atk1_ref})'
    
    parts = []
    for r in rival_nicks:
        sc = sh_eval_map.get(r, {}).get('score', 0)
        parts.append((r, sc))
        
    formula = f'"🛡️ Recomendado: " & {c_atk1_ref}'
    for r_a, sc_a in parts:
        if sc_a >= 1:
            formula = f'IF({c_atk1_ref}="{r_a}", "🛡️ Favorable (+1): {r_a}", {formula})'
        elif sc_a <= -1:
            formula = f'IF({c_atk1_ref}="{r_a}", "🛡️ Evitar {r_a} -> Elegir: " & {c_atk2_ref}, {formula})'
            
    return f'=IF(OR({c_atk1_ref}="", {c_atk2_ref}=""), "Esperando asignación", {formula})'

def export_to_gsheet(event_id: str, event_data: dict) -> str:
    """
    Crea DIRECTAMENTE un nuevo Google Sheet online en Google Drive
    con soporte dinámico para 3, 5 o 7 jugadores y asignación dinámica de roles WTC.
    """
    client = get_gspread_client()
    
    config = get_or_set_team_config(event_id, event_data)
    ref_team_name = config.get('reference_team', '')
    profiles_data = load_or_create_profiles(event_id, event_data, ref_team_name)
    
    our_players = profiles_data.get('players', [])
    team_size = len(our_players)
    num_shields, num_spears = calculate_roles_distribution(team_size)
    
    sheet_title = f"Longshanks Event #{event_id} - Listas por Equipos ({team_size}P)"
    print(f"[*] Creando Google Sheet online directamente: '{sheet_title}'...", flush=True)
    
    sh = client.create(sheet_title)
    
    # Pestaña 1: Resumen Torneo
    ws_summary = sh.sheet1
    ws_summary.update_title("Resumen Torneo")
    
    summary_rows = [
        [f"Longshanks Event #{event_id} - Resumen por Equipos ({team_size} Jugadores)"],
        [f"Equipo de Referencia: {ref_team_name} ({num_shields} Escudos / {num_spears} Lanzas)"],
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
    
    # Pestañas por Cada Equipo
    teams = event_data.get('teams', [])
    
    for team in teams:
        t_name = team.get('team_name', 'Equipo')[:31]
        is_our_team = (t_name.strip().lower() == ref_team_name.strip().lower())
        players_data = team.get('players_data', [])
        
        tab_name = f"NUESTRO - {t_name}"[:31] if is_our_team else t_name
        ws_team = sh.add_worksheet(title=tab_name, rows=50, cols=max(len(players_data) + 5, 10))
        
        if not players_data:
            ws_team.update(range_name="A1", values=[[f"Equipo: {t_name}"], ["Sin listas registradas"]])
            continue
            
        if is_our_team:
            our_rows = [
                [f"🛡️ NUESTRO EQUIPO DE REFERENCIA: {t_name}"],
                [f"Configuración: {team_size} Jugadores ({num_shields} Escudos / {num_spears} Lanzas)"],
                [],
                ["Alias", "Nombre Completo", "Facción", "Arquetipo / Concepto", "Afinidad Defensiva", "Criterios Favorables", "Criterios Desfavorables", "Notas de Experiencia"]
            ]
            for p_prof in our_players:
                our_rows.append([
                    p_prof.get('alias', ''),
                    p_prof.get('player_name', ''),
                    p_prof.get('faction', ''),
                    p_prof.get('archetype', ''),
                    p_prof.get('defensive_affinity', ''),
                    ", ".join(p_prof.get('favorable', [])),
                    ", ".join(p_prof.get('unfavorable', [])),
                    p_prof.get('custom_notes', '')
                ])
            ws_team.update(range_name="A1", values=our_rows)
            continue
            
        roles_analysis = determine_roles_for_rival_team(profiles_data, players_data)
        matrix = roles_analysis['matrix']
        net_scores = roles_analysis['net_scores']
        shields_names = roles_analysis['shields_names']
        spears_names = roles_analysis['spears_names']
        rival_best_spears = roles_analysis['rival_best_spears_map']
        
        rival_nicks = [p.get('player_name', f'Rival {i+1}') for i, p in enumerate(players_data)]
        
        matrix_headers = ["Jugador", "Arquetipo / Concepto", "Rol vs Rival"]
        for r_nick in rival_nicks:
            matrix_headers.append(f"vs {r_nick}")
        matrix_headers.append("Balance Net Score")
        
        matrix_rows = [
            [f"Equipo Rival: {t_name}"],
            [],
            [f"🎯 MATRIZ DE EMPAREJAMIENTOS {team_size}x{len(players_data)} ({ref_team_name} vs {t_name})"],
            matrix_headers
        ]
        
        for p_prof in our_players:
            alias = p_prof.get('alias') or p_prof.get('player_name')
            if alias in shields_names:
                role_label = f"🛡️ Escudo #{shields_names.index(alias) + 1}"
            else:
                role_label = f"⚔️ Lanza #{spears_names.index(alias) + 1}"
                
            row_eval = [alias, p_prof.get('archetype', ''), role_label]
            for r_nick in rival_nicks:
                eval_info = matrix.get(alias, {}).get(r_nick, {'score': 0, 'symbol': '🟡'})
                row_eval.append(f"{eval_info['symbol']} ({eval_info['score']:+d})")
            row_eval.append(f"{net_scores.get(alias, 0):+d}")
            matrix_rows.append(row_eval)
            
        matrix_rows.append([])
        matrix_rows.append(["🎛️ ASISTENTE DE PAIRING EN MESA (PANEL DE CONTROL WTC)"])
        
        picked_spear_cell_refs = []
        picked_rival_cell_refs = []
        
        for k in range(num_shields):
            sh_num = k + 1
            sh_name = shields_names[k] if k < len(shields_names) else f"Escudo {sh_num}"
            
            step1_emoji = STEP_EMOJIS.get(3 * k + 1, f"[{3*k + 1}]")
            step2_emoji = STEP_EMOJIS.get(3 * k + 2, f"[{3*k + 2}]")
            step3_emoji = STEP_EMOJIS.get(3 * k + 3, f"[{3*k + 3}]")
            
            r_def_default = rival_nicks[k * 2] if (k * 2) < len(rival_nicks) else (rival_nicks[0] if rival_nicks else "")
            r_atk1_default = rival_nicks[k * 2 + 1] if (k * 2 + 1) < len(rival_nicks) else r_def_default
            r_atk2_default = rival_nicks[k * 2 + 2] if (k * 2 + 2) < len(rival_nicks) else r_atk1_default
            
            matrix_rows.append([f"TANDA {sh_num} (Emparejamientos {2*k + 1} y {2*k + 2})"])
            matrix_rows.append([f"[OFERTA {sh_num}A] Su Defensor #{sh_num} -> Nuestras Lanzas", "", f"[OFERTA {sh_num}B] Nuestro Escudo #{sh_num} ({sh_name}) -> Sus Atacantes"])
            
            r_def_row = len(matrix_rows) + 1
            matrix_rows.append([f"{step1_emoji} Defensor Rival #{sh_num} revelado:", r_def_default, f"• Atacante Rival #{sh_num}A para {sh_name}:", r_atk1_default])
            picked_rival_cell_refs.append(f"B{r_def_row}")
            
            rec_spears_row = len(matrix_rows) + 1
            if k == 0:
                spears_formula = build_spears_formula(f"B{r_def_row}", rival_best_spears)
            else:
                prev_pick = picked_spear_cell_refs[-1]
                if len(spears_names) == 3:
                    spears_formula = f'=IF({prev_pick}="{spears_names[0]}", "⚔️ {spears_names[1]} y {spears_names[2]}", IF({prev_pick}="{spears_names[1]}", "⚔️ {spears_names[0]} y {spears_names[2]}", "⚔️ {spears_names[0]} y {spears_names[1]}"))'
                else:
                    spears_formula = f'"⚔️ Lanzas activas restantes Tanda {sh_num}"'
                    
            matrix_rows.append([f"💡 Nuestras Lanzas recomendadas Tanda {sh_num}:", spears_formula, f"• Atacante Rival #{sh_num}B para {sh_name}:", r_atk2_default])
            
            pick_row = len(matrix_rows) + 1
            def_spear_pick = spears_names[min(k, len(spears_names) - 1)]
            rec_shield_formula = build_shield_rec_formula(sh_name, f"D{r_def_row}", f"D{rec_spears_row}", matrix.get(sh_name, {}), rival_nicks)
            
            matrix_rows.append([f"{step2_emoji} ¿Qué Lanza aceptó el rival?:", def_spear_pick, f"💡 Recomendación para {sh_name}:", rec_shield_formula])
            picked_spear_cell_refs.append(f"B{pick_row}")
            
            final_atk_row = len(matrix_rows) + 1
            matrix_rows.append(["", "", f"{step3_emoji} Atacante Rival aceptado para {sh_name}:", r_atk1_default])
            picked_rival_cell_refs.append(f"D{final_atk_row}")
            matrix_rows.append([])
            
        # Cruce final por descarte
        rival_checks = []
        for r_n in rival_nicks:
            conds = [f'{cell}="{r_n}"' for cell in picked_rival_cell_refs]
            or_cond = f'OR({", ".join(conds)})'
            rival_checks.append((r_n, or_cond))
            
        formula_rival_restante = f'"{rival_nicks[-1]}"'
        for r_n, cond in reversed(rival_checks[:-1]):
            formula_rival_restante = f'IF({cond}, {formula_rival_restante}, "{r_n}")'

        if len(spears_names) == 2:
            p1_ref = picked_spear_cell_refs[0]
            formula_lanza_restante = f'IF({p1_ref}="{spears_names[0]}", "⚔️ {spears_names[1]}", "⚔️ {spears_names[0]}")'
        elif len(spears_names) == 3:
            p1_ref = picked_spear_cell_refs[0]
            p2_ref = picked_spear_cell_refs[1]
            s0, s1, s2 = spears_names[0], spears_names[1], spears_names[2]
            formula_lanza_restante = f'IF(AND({p1_ref}<>"{s0}", {p2_ref}<>"{s0}"), "⚔️ {s0}", IF(AND({p1_ref}<>"{s1}", {p2_ref}<>"{s1}"), "⚔️ {s1}", "⚔️ {s2}"))'
        else:
            formula_lanza_restante = '"⚔️ Lanza no asignada"'

        matrix_rows.append([f"⚡ Cruce {team_size} (Automático por descarte final):", f'={formula_lanza_restante} & " vs " & {formula_rival_restante}'])
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
            row_lists.append("\n".join(lines) if lines else "Sin lista registrada")
            
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
    print(f"\n[SUCCESS] Google Sheet creado dinámicamente ({team_size} jugadores)!")
    print(f"🔗 Enlace directo: {url}", flush=True)
    return url
