import re
import os
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

from src.config import OUTPUT_DIR
from src.team_manager import (
    load_or_create_profiles, get_or_set_team_config, calculate_roles_distribution
)
from src.matrix_evaluator import determine_roles_for_rival_team
from src.storage import load_event_schedule

STEP_EMOJIS = {
    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
}

def sanitize_sheet_title(name: str) -> str:
    if not name:
        return "Equipo"
    for ch in ['\\', '/', '?', '*', ':', '[', ']']:
        name = name.replace(ch, '')
    clean_name = name.strip()
    return clean_name[:31] if clean_name else "Equipo"

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
    """
    Construye una fórmula IF que recomienda el rival con mejor score para el Escudo
    dentro del rango de 5 niveles: +2 (Ideal), +1 (Favorable), 0 (Igualado), -1 (Desfavorable), -2 (Crítico).
    """
    if not rival_nicks:
        return f'=IF({c_atk1_ref}="", "Esperando asignación", "🛡️ " & {c_atk1_ref})'
    
    parts = []
    for r in rival_nicks:
        sc = sh_eval_map.get(r, {}).get('score', 0)
        parts.append((r, sc))
        
    formula = f'"🛡️ Recomendado: " & {c_atk1_ref}'
    for r_a, sc_a in parts:
        if sc_a == 2:
            formula = f'IF({c_atk1_ref}="{r_a}", "🟢🟢 ¡Ideal (+2)!: {r_a}", {formula})'
        elif sc_a == 1:
            formula = f'IF({c_atk1_ref}="{r_a}", "🟢 Favorable (+1): {r_a}", {formula})'
        elif sc_a == -2:
            formula = f'IF({c_atk1_ref}="{r_a}", "⛔ ¡EVITAR (-2) {r_a}! -> Elegir: " & {c_atk2_ref}, {formula})'
        elif sc_a == -1:
            formula = f'IF({c_atk1_ref}="{r_a}", "🟠 Desfavorable (-1) -> Preferir: " & {c_atk2_ref}, {formula})'
            
    return f'=IF(OR({c_atk1_ref}="", {c_atk2_ref}=""), "Esperando asignación", {formula})'

def export_to_excel(event_id: str, event_data: dict, output_filename: str = None) -> str:
    """
    Genera un libro de Excel (.xlsx) completamente interactivo y adaptativo
    para torneos de 3, 5 o 7 jugadores con asignación dinámica de roles WTC por rival.
    """
    if not output_filename:
        output_filename = os.path.join(OUTPUT_DIR, f"event_{event_id}_listas.xlsx")
    elif not os.path.isabs(output_filename):
        output_filename = os.path.join(OUTPUT_DIR, output_filename)

    config = get_or_set_team_config(event_id, event_data)
    ref_team_name = config.get('reference_team', '')
    profiles_data = load_or_create_profiles(event_id, event_data, ref_team_name)
    
    our_players = profiles_data.get('players', [])
    team_size = len(our_players)
    num_shields, num_spears = calculate_roles_distribution(team_size)

    wb = openpyxl.Workbook()

    # Estilos de Excel
    font_title = Font(name='Segoe UI', size=14, bold=True, color='1F4E78')
    font_section_title = Font(name='Segoe UI', size=11, bold=True, color='1F4E78')
    font_header = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
    font_player_header = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
    font_faction = Font(name='Segoe UI', size=9, italic=True, color='595959')
    font_points = Font(name='Segoe UI', size=9, bold=True, color='2F5597')
    font_link = Font(name='Segoe UI', size=9, bold=True, color='0563C1', underline='single')
    font_normal = Font(name='Segoe UI', size=9)
    font_bold = Font(name='Segoe UI', size=9, bold=True)
    font_interactive = Font(name='Segoe UI', size=9, bold=True, color='1F4E78')

    # Fuentes y Fills para los 5 niveles de emparejamiento (-2 a +2)
    font_p2 = Font(name='Segoe UI', size=9, bold=True, color='006100')
    font_p1 = Font(name='Segoe UI', size=9, bold=True, color='276A3C')
    font_c0 = Font(name='Segoe UI', size=9, bold=True, color='8C6B00')
    font_m1 = Font(name='Segoe UI', size=9, bold=True, color='B25900')
    font_m2 = Font(name='Segoe UI', size=9, bold=True, color='9C0006')

    # Alias de compatibilidad
    font_green = font_p1
    font_yellow = font_c0
    font_red = font_m2

    fill_p2 = PatternFill(start_color='FFA2D9A2', end_color='FFA2D9A2', fill_type='solid') # Verde bosque/intenso (+2)
    fill_p1 = PatternFill(start_color='FFC6EFCE', end_color='FFC6EFCE', fill_type='solid') # Verde menta claro (+1)
    fill_c0 = PatternFill(start_color='FFFFEB9C', end_color='FFFFEB9C', fill_type='solid') # Amarillo estándar (0)
    fill_m1 = PatternFill(start_color='FFFCE4D6', end_color='FFFCE4D6', fill_type='solid') # Salmón / Naranja suave (-1)
    fill_m2 = PatternFill(start_color='FFFFC7CE', end_color='FFFFC7CE', fill_type='solid') # Rojo intenso (-2)

    # Alias de compatibilidad
    fill_green = fill_p1
    fill_yellow = fill_c0
    fill_red = fill_m2

    fill_team_header = PatternFill(start_color='FF1F4E78', end_color='FF1F4E78', fill_type='solid')
    fill_player_header = PatternFill(start_color='FF2F5597', end_color='FF2F5597', fill_type='solid')
    fill_matrix_header = PatternFill(start_color='FF366092', end_color='FF366092', fill_type='solid')
    fill_tanda_headers = [
        PatternFill(start_color='FF2E75B6', end_color='FF2E75B6', fill_type='solid'), # Tanda 1 Azul
        PatternFill(start_color='FFC55A11', end_color='FFC55A11', fill_type='solid'), # Tanda 2 Naranja
        PatternFill(start_color='FF7030A0', end_color='FF7030A0', fill_type='solid'), # Tanda 3 Púrpura
    ]
    fill_card_content = PatternFill(start_color='FFDCE1E7', end_color='FFDCE1E7', fill_type='solid')   # Gris suave antifatiga visible
    fill_zebra = PatternFill(start_color='FFCFD6DC', end_color='FFCFD6DC', fill_type='solid')          # Fila alterna gris suave
    fill_recommend_box = PatternFill(start_color='FFCBD2D9', end_color='FFCBD2D9', fill_type='solid')  # Panel WTC gris neutro
    fill_interactive_box = PatternFill(start_color='FFBAC4CE', end_color='FFBAC4CE', fill_type='solid')# Desplegable interactivo

    thin_side = Side(border_style="thin", color="8A96A3")
    thick_bottom = Side(border_style="medium", color="1F4E78")
    border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    border_header = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thick_bottom)

    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_top_left = Alignment(horizontal='left', vertical='top', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center')

    # -------------------------------------------------------------
    # Pestaña 1: Resumen General del Torneo
    # -------------------------------------------------------------
    ws_summary = wb.active
    ws_summary.title = "Resumen Torneo"
    ws_summary.views.sheetView[0].showGridLines = True

    ws_summary.cell(row=1, column=1, value=f"Longshanks Event #{event_id} - Resumen por Equipos (Equipos de {team_size})").font = font_title
    ws_summary.cell(row=2, column=1, value=f"Equipo de Referencia: {ref_team_name} ({num_shields} Escudos / {num_spears} Lanzas por ronda)").font = font_bold

    headers_summary = ["Equipo", "ID Jugador", "Jugador / Nick", "Facción", "Puntos"]
    for col_num, h_text in enumerate(headers_summary, 1):
        cell = ws_summary.cell(row=4, column=col_num, value=h_text)
        cell.font = font_header
        cell.fill = fill_team_header
        cell.alignment = align_center
        cell.border = border_header

    current_row = 5
    for team in event_data.get('teams', []):
        t_name = team.get('team_name', 'Desconocido')
        for p in team.get('players_data', []):
            ws_summary.cell(row=current_row, column=1, value=t_name).font = font_normal
            ws_summary.cell(row=current_row, column=2, value=p.get('player_id', '')).font = font_normal
            ws_summary.cell(row=current_row, column=3, value=p.get('player_name', '')).font = font_normal
            ws_summary.cell(row=current_row, column=4, value=p.get('faction', '')).font = font_faction
            ws_summary.cell(row=current_row, column=5, value=p.get('points', '')).font = font_points

            for col_num in range(1, 6):
                c = ws_summary.cell(row=current_row, column=col_num)
                c.border = border_cell
                c.fill = fill_zebra if current_row % 2 == 0 else fill_card_content
            current_row += 1

    for col in ws_summary.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_summary.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # -------------------------------------------------------------
    # Pestaña 2: Calendario y Misiones del Torneo (Rondas 1 a 5)
    # -------------------------------------------------------------
    schedule_data = load_event_schedule(event_id)
    used_titles = set(["Resumen Torneo"])

    if schedule_data and schedule_data.get('rounds'):
        sched_title = "Calendario y Misiones"
        ws_sched = wb.create_sheet(title=sched_title)
        used_titles.add(sched_title)
        ws_sched.views.sheetView[0].showGridLines = True

        ws_sched.cell(row=1, column=1, value=f"Longshanks Event #{event_id} - Calendario de Rondas y Misiones Oficiales (X-Wing 2.5)").font = font_title
        ws_sched.cell(row=2, column=1, value=f"Equipo de Referencia: {ref_team_name} | Emparejamientos y Problemática Táctica por Escenario WTC").font = font_bold

        # TABLA 1: Hoja de Ruta de Team Spain
        ws_sched.cell(row=4, column=1, value=f"🎯 HOJA DE RUTA DE {ref_team_name.upper()} (EMPAREJAMIENTO Y MISIÓN POR RONDA)").font = font_section_title
        sched_headers = ["Ronda", "Rival de España", "Misión / Escenario", "Formato de Objetivos", "Problemática Táctica para la Selección", "Asesoría para Lanzas y Escudos"]
        for c_idx, h in enumerate(sched_headers, 1):
            c = ws_sched.cell(row=5, column=c_idx, value=h)
            c.font = font_header; c.fill = fill_team_header; c.alignment = align_center; c.border = border_header

        curr_s_row = 6
        for rnd in schedule_data.get('rounds', []):
            r_num = f"Ronda {rnd.get('round_number')}"
            r_opp = rnd.get('spain_opponent', '')
            r_mis = f"{rnd.get('mission_name')} ({rnd.get('mission_name_es')})"
            sc_det = rnd.get('scenario_details', {})
            r_lay = sc_det.get('objectives_layout', '')
            r_imp = sc_det.get('tactical_impact', '')
            r_adv = sc_det.get('team_spain_advice', '')

            fill_row = fill_zebra if curr_s_row % 2 == 0 else fill_card_content

            c1 = ws_sched.cell(row=curr_s_row, column=1, value=r_num)
            c1.font = font_bold; c1.alignment = align_center; c1.fill = fill_row; c1.border = border_cell

            c2 = ws_sched.cell(row=curr_s_row, column=2, value=r_opp)
            c2.font = font_bold; c2.alignment = align_center; c2.fill = fill_row; c2.border = border_cell

            c3 = ws_sched.cell(row=curr_s_row, column=3, value=r_mis)
            c3.font = font_interactive; c3.fill = fill_row; c3.border = border_cell

            c4 = ws_sched.cell(row=curr_s_row, column=4, value=r_lay)
            c4.font = font_normal; c4.fill = fill_row; c4.border = border_cell

            c5 = ws_sched.cell(row=curr_s_row, column=5, value=r_imp)
            c5.font = font_normal; c5.fill = fill_row; c5.border = border_cell

            c6 = ws_sched.cell(row=curr_s_row, column=6, value=r_adv)
            c6.font = font_bold; c6.fill = fill_row; c6.border = border_cell

            curr_s_row += 1

        # TABLA 2: Cuadrante de Emparejamientos por Ronda (Grupo)
        curr_s_row += 2
        ws_sched.cell(row=curr_s_row, column=1, value="📋 CUADRANTE DE EMPAREJAMIENTOS DEL GRUPO (RONDAS 1 A 5)").font = font_section_title
        curr_s_row += 1

        grid_headers = ["Ronda", "Misión del Escenario", "Mesa 1", "Mesa 2", "Mesa 3"]
        for c_idx, h in enumerate(grid_headers, 1):
            c = ws_sched.cell(row=curr_s_row, column=c_idx, value=h)
            c.font = font_header; c.fill = fill_matrix_header; c.alignment = align_center; c.border = border_header
        curr_s_row += 1

        for rnd in schedule_data.get('rounds', []):
            fill_row = fill_zebra if curr_s_row % 2 == 0 else fill_card_content
            r_num = f"Ronda {rnd.get('round_number')}"
            r_mis = f"{rnd.get('mission_name')} ({rnd.get('mission_name_es')})"
            pairings = rnd.get('pairings', [])

            c1 = ws_sched.cell(row=curr_s_row, column=1, value=r_num)
            c1.font = font_bold; c1.alignment = align_center; c1.fill = fill_row; c1.border = border_cell

            c2 = ws_sched.cell(row=curr_s_row, column=2, value=r_mis)
            c2.font = font_interactive; c2.fill = fill_row; c2.border = border_cell

            for p_idx, pair in enumerate(pairings[:3], 3):
                t_a = pair.get('team_a', '')
                t_b = pair.get('team_b', '')
                pair_str = f"{t_a} vs. {t_b}"
                is_spain_pair = ('spain' in t_a.lower() or 'spain' in t_b.lower())
                if is_spain_pair:
                    pair_str = f"🎯 {pair_str}"

                cp = ws_sched.cell(row=curr_s_row, column=p_idx, value=pair_str)
                cp.font = font_bold if is_spain_pair else font_normal
                cp.alignment = align_center
                cp.fill = fill_p1 if is_spain_pair else fill_row
                cp.border = border_cell
            curr_s_row += 1

        # TABLA 3: Guía Táctica de los 5 Escenarios (X-Wing 2.5 WTC)
        curr_s_row += 2
        ws_sched.cell(row=curr_s_row, column=1, value="📖 GUÍA TÁCTICA DE ESCENARIOS (X-WING 2.5 WTC)").font = font_section_title
        curr_s_row += 1

        guide_headers = ["Escenario", "Mecánica de Puntuación", "Problemática Clave", "Listas de 3 Naves", "Enjambres (6-8 Naves)", "Recomendación para Selección"]
        for c_idx, h in enumerate(guide_headers, 1):
            c = ws_sched.cell(row=curr_s_row, column=c_idx, value=h)
            c.font = font_header; c.fill = fill_team_header; c.alignment = align_center; c.border = border_header
        curr_s_row += 1

        impacts_3_ships = {
            1: "Muy Desfavorable: Dividirse en 5 satélites regala naves aisladas. Obligados a volar en grupo cerrado y forzar aniquilación temprana antes de perder en puntos.",
            2: "Desfavorable: Cargar una caja en una nave pesada/as le quita el 33% del ataque o maniobra. Ignorar cajas al inicio y matar rápido a las mulas enemigas.",
            3: "Manejable: Solo 3 satélites en la línea central neutral. El combate es compacto y no hay que dispersarse por las esquinas.",
            4: "Neutro: Balizas con acción R1. Para España es Ronda de Descanso (BYE).",
            5: "ÓPTIMO / IDEAL (+2): 95% combate puro. No hay dispersión ni transporte de cajas. Volar en bloque y aniquilar en el primer cruce frontal."
        }

        impacts_swarms = {
            1: "ÓPTIMO / IDEAL (+2): Destinar 2 naves baratas a satélites exteriores puntúa 2-3 VP/turno pasivos mientras 6 naves traban al enemigo en el centro.",
            2: "Favorable: Dispone de múltiples naves baratas (mulas de 9-11 pts) para recoger y proteger cajas sin comprometer el ataque del escuadrón.",
            3: "Favorable: Naves de I1 bloquean físicamente sobre los satélites o deniegan el paso a los ases enemigos antes de interactuar.",
            4: "Favorable: Múltiples fuentes de acción para activar balizas.",
            5: "Desfavorable (-1): Pierden la ventaja de puntos pasivos por objetivos. Cada nave barata derribada regala puntos en la carrera directa de daño."
        }

        for rnd in schedule_data.get('rounds', []):
            fill_row = fill_zebra if curr_s_row % 2 == 0 else fill_card_content
            sc = rnd.get('scenario_details', {})
            r_id = rnd.get('round_number')
            m_title = f"Ronda {r_id}:\n{rnd.get('mission_name')}\n({rnd.get('mission_name_es')})"

            c1 = ws_sched.cell(row=curr_s_row, column=1, value=m_title)
            c1.font = font_bold; c1.alignment = align_center; c1.fill = fill_row; c1.border = border_cell

            c2 = ws_sched.cell(row=curr_s_row, column=2, value=sc.get('scoring_mechanics', ''))
            c2.font = font_normal; c2.alignment = align_top_left; c2.fill = fill_row; c2.border = border_cell

            c3 = ws_sched.cell(row=curr_s_row, column=3, value=sc.get('tactical_impact', ''))
            c3.font = font_normal; c3.alignment = align_top_left; c3.fill = fill_row; c3.border = border_cell

            c4 = ws_sched.cell(row=curr_s_row, column=4, value=impacts_3_ships.get(r_id, ''))
            c4.font = font_faction; c4.alignment = align_top_left; c4.fill = fill_row; c4.border = border_cell

            c5 = ws_sched.cell(row=curr_s_row, column=5, value=impacts_swarms.get(r_id, ''))
            c5.font = font_faction; c5.alignment = align_top_left; c5.fill = fill_row; c5.border = border_cell

            c6 = ws_sched.cell(row=curr_s_row, column=6, value=sc.get('team_spain_advice', ''))
            c6.font = font_bold; c6.alignment = align_top_left; c6.fill = fill_row; c6.border = border_cell

            curr_s_row += 1

        ws_sched.column_dimensions['A'].width = 18
        ws_sched.column_dimensions['B'].width = 30
        ws_sched.column_dimensions['C'].width = 34
        ws_sched.column_dimensions['D'].width = 34
        ws_sched.column_dimensions['E'].width = 40
        ws_sched.column_dimensions['F'].width = 44

    # -------------------------------------------------------------
    # Pestañas por Cada Equipo Rival
    # -------------------------------------------------------------

    for team in event_data.get('teams', []):
        t_name = team.get('team_name', 'Equipo')
        is_our_team = (t_name.strip().lower() == ref_team_name.strip().lower())
        
        sheet_title = sanitize_sheet_title(f"NUESTRO - {t_name}" if is_our_team else t_name)
        base_title = sheet_title
        counter = 1
        while sheet_title in used_titles:
            suffix = f" ({counter})"
            sheet_title = base_title[:31 - len(suffix)] + suffix
            counter += 1
        used_titles.add(sheet_title)

        ws_team = wb.create_sheet(title=sheet_title)
        ws_team.views.sheetView[0].showGridLines = True

        players_data = team.get('players_data', [])
        if not players_data:
            ws_team.cell(row=1, column=1, value=f"Equipo: {t_name}").font = font_title
            ws_team.cell(row=3, column=1, value="No se encontraron listas registradas para este equipo.").font = font_normal
            continue

        if is_our_team:
            ws_team.cell(row=1, column=1, value=f"🛡️ NUESTRO EQUIPO DE REFERENCIA: {t_name}").font = font_title
            ws_team.cell(row=2, column=1, value=f"Configuración: {team_size} Jugadores ({num_shields} Escudos / {num_spears} Lanzas)").font = font_bold
            
            ws_team.cell(row=4, column=1, value="FICHAS DE PERFILADO Y REGLAS DE LISTA (data/event_" + str(event_id) + "_profiles.json)").font = font_section_title
            prof_headers = [
                "Alias", "Nombre Completo", "Facción", "Arquetipo / Concepto",
                "Criterios Favorables (🟢 / 🟢🟢)", "Criterios Desfavorables (🟠 / 🔴🔴)",
                "Checks Vulnerabilidades (Control)",
                "Notas del Jugador / Propuesta", "Asesor Táctico (Advisor IA)"
            ]
            for c_i, h in enumerate(prof_headers, 1):
                c = ws_team.cell(row=5, column=c_i, value=h)
                c.font = font_header; c.fill = fill_team_header; c.alignment = align_center; c.border = border_header
                
            last_prof_row = 5
            for r_i, p_prof in enumerate(our_players, 6):
                last_prof_row = r_i
                fill_row = fill_zebra if r_i % 2 == 0 else fill_card_content

                ws_team.cell(row=r_i, column=1, value=p_prof.get('alias', '')).font = font_bold
                ws_team.cell(row=r_i, column=2, value=p_prof.get('player_name', '')).font = font_normal
                ws_team.cell(row=r_i, column=3, value=p_prof.get('faction', '')).font = font_faction
                ws_team.cell(row=r_i, column=4, value=p_prof.get('archetype', '')).font = font_normal
                ws_team.cell(row=r_i, column=5, value=", ".join(p_prof.get('favorable', []))).font = font_green
                ws_team.cell(row=r_i, column=6, value=", ".join(p_prof.get('unfavorable', []))).font = font_red
                
                vulns = p_prof.get('vulnerabilities', {})
                if vulns:
                    v_labels = [
                        ('bombas', '💣 Bombas'),
                        ('estres', '⚡ Estrés'),
                        ('iones', '🔵 Iones'),
                        ('jam', '📡 Jam'),
                        ('tractores', '🧲 Tractores')
                    ]
                    v_parts = [f"{lbl}: {'⚠️' if vulns.get(k) else '🛡️'}" for k, lbl in v_labels]
                    c7_val = "\n".join(v_parts)
                else:
                    c7_val = "Estándar"
                    
                c7 = ws_team.cell(row=r_i, column=7, value=c7_val)
                c7.font = font_normal
                c7.alignment = align_top_left
                
                c8 = ws_team.cell(row=r_i, column=8, value=p_prof.get('custom_notes', ''))
                c8.font = font_normal
                c8.alignment = align_top_left
                
                c9 = ws_team.cell(row=r_i, column=9, value=p_prof.get('tactical_advisor', ''))
                c9.font = font_normal
                c9.alignment = align_top_left
                
                ws_team.row_dimensions[r_i].height = 80
                for c_i in range(1, 10):
                    c = ws_team.cell(row=r_i, column=c_i)
                    c.border = border_cell
                    c.fill = fill_row
                    
            prof_col_widths = {1: 12, 2: 24, 3: 20, 4: 32, 5: 28, 6: 28, 7: 22, 8: 48, 9: 48}
            for c_i, w in prof_col_widths.items():
                ws_team.column_dimensions[get_column_letter(c_i)].width = w
                    
            lists_title_row = last_prof_row + 2
            ws_team.cell(row=lists_title_row, column=1, value="LISTAS COMPLETAS DE NUESTROS INTEGRANTES").font = font_section_title
            for col_idx, p_data in enumerate(players_data, 1):
                raw_xws = p_data.get('raw_xws', '')
                yasb_link = ""
                if raw_xws:
                    try:
                        js_x = json.loads(raw_xws)
                        yasb_link = js_x.get('vendor', {}).get('yasb', {}).get('link') or js_x.get('vendor', {}).get('lbn', {}).get('link') or ""
                    except Exception:
                        pass

                c_np = ws_team.cell(row=lists_title_row + 1, column=col_idx, value=p_data.get('player_name', ''))
                c_np.font = font_player_header; c_np.fill = fill_player_header; c_np.alignment = align_center; c_np.border = border_header

                c_lp = ws_team.cell(row=lists_title_row + 2, column=col_idx)
                if yasb_link:
                    c_lp.value = "🔗 Abrir lista en YASB"
                    c_lp.hyperlink = yasb_link
                    c_lp.font = font_link
                else:
                    c_lp.value = ""
                c_lp.fill = fill_card_content; c_lp.alignment = align_center; c_lp.border = border_cell

                c_tx = ws_team.cell(row=lists_title_row + 3, column=col_idx, value="\n".join(p_data.get('list_lines', [])))
                c_tx.font = font_normal; c_tx.fill = fill_card_content; c_tx.alignment = align_top_left; c_tx.border = border_cell

                if col_idx > 8:
                    ws_team.column_dimensions[get_column_letter(col_idx)].width = 44
            continue

        # =========================================================
        # EQUIPO RIVAL: EVALUACIÓN NxN Y ASISTENTE DINÁMICO WTC
        # =========================================================
        scheduled_rnd = None
        if schedule_data and schedule_data.get('rounds'):
            norm_t = t_name.strip().lower()
            for r_entry in schedule_data['rounds']:
                sp_opp = r_entry.get('spain_opponent', '').strip().lower()
                if sp_opp and (sp_opp == norm_t or sp_opp in norm_t or norm_t in sp_opp):
                    scheduled_rnd = r_entry
                    break

        if scheduled_rnd:
            r_num = scheduled_rnd.get('round_number')
            m_name = scheduled_rnd.get('mission_name')
            m_name_es = scheduled_rnd.get('mission_name_es')
            sc_info = scheduled_rnd.get('scenario_details', {})
            
            c_t1 = ws_team.cell(row=1, column=1, value=f"⚔️ EQUIPO RIVAL: {t_name.upper()} | 🎯 CRUCE OFICIAL: RONDA {r_num} vs {ref_team_name.upper()}")
            c_t1.font = font_title
            
            c_m = ws_team.cell(row=2, column=1, value=f"📍 Misión Oficial: {m_name} ({m_name_es}) — Objetivos: {sc_info.get('objectives_layout', '')}")
            c_m.font = font_bold
            
            c_tip = ws_team.cell(row=3, column=1, value=f"💡 Problemática Táctica: {sc_info.get('tactical_impact', '')}")
            c_tip.font = font_faction
            
            c_adv = ws_team.cell(row=4, column=1, value=f"🛡️ Asesoría para Selección: {sc_info.get('team_spain_advice', '')}")
            c_adv.font = font_interactive
            
            start_matrix_title_row = 6
        else:
            ws_team.cell(row=1, column=1, value=f"Equipo Rival: {t_name}").font = font_title
            start_matrix_title_row = 3

        roles_analysis = determine_roles_for_rival_team(profiles_data, players_data)
        matrix = roles_analysis['matrix']
        net_scores = roles_analysis['net_scores']
        shields_names = roles_analysis['shields_names']
        spears_names = roles_analysis['spears_names']
        rival_best_spears = roles_analysis['rival_best_spears_map']

        rival_nicks = [p.get('player_name', f'Rival {i+1}') for i, p in enumerate(players_data)]

        # ---------------------------------------------------------
        # BLOQUE A: MATRIZ DE EMPAREJAMIENTOS NxN
        # ---------------------------------------------------------
        ws_team.cell(row=start_matrix_title_row, column=1, value=f"🎯 MATRIZ DE EMPAREJAMIENTOS {team_size}x{len(players_data)} ({ref_team_name} vs {t_name})  [🟢🟢 +2 Ideal | 🟢 +1 Favorable | 🟡 0 Parejo | 🟠 -1 Desfavorable | 🔴🔴 -2 Crítico]").font = font_section_title

        headers_matrix = ["Jugador", "Arquetipo / Concepto", "Rol vs Rival"]
        for r_nick in rival_nicks:
            headers_matrix.append(f"vs {r_nick}")
        headers_matrix.append("Balance Net Score")

        headers_matrix_row = start_matrix_title_row + 1
        for col_idx, h_text in enumerate(headers_matrix, 1):
            c = ws_team.cell(row=headers_matrix_row, column=col_idx, value=h_text)
            c.font = font_header; c.fill = fill_matrix_header; c.alignment = align_center; c.border = border_header

        m_row = headers_matrix_row + 1
        for p_prof in our_players:
            alias = p_prof.get('alias') or p_prof.get('player_name')
            fill_m_row = fill_zebra if m_row % 2 == 0 else fill_card_content

            c_name = ws_team.cell(row=m_row, column=1, value=alias)
            c_name.font = font_bold; c_name.fill = fill_m_row; c_name.border = border_cell

            c_arch = ws_team.cell(row=m_row, column=2, value=p_prof.get('archetype', ''))
            c_arch.font = font_faction; c_arch.fill = fill_m_row; c_arch.border = border_cell

            if alias in shields_names:
                sh_idx = shields_names.index(alias) + 1
                role_label = f"🛡️ Escudo #{sh_idx}"
            else:
                sp_idx = spears_names.index(alias) + 1
                role_label = f"⚔️ Lanza #{sp_idx}"
            c_role = ws_team.cell(row=m_row, column=3, value=role_label)
            c_role.font = font_bold; c_role.fill = fill_m_row; c_role.alignment = align_center; c_role.border = border_cell

            col_eval = 4
            for r_nick in rival_nicks:
                eval_info = matrix.get(alias, {}).get(r_nick, {'score': 0, 'symbol': '🟡', 'reason': ''})
                sc = eval_info['score']
                sym = eval_info['symbol']

                c_res = ws_team.cell(row=m_row, column=col_eval, value=f"{sym} ({sc:+d})")
                c_res.alignment = align_center; c_res.border = border_cell
                if eval_info.get('reason'):
                    c_res.comment = Comment(eval_info['reason'], "Matriz Táctica")
                if sc == 2:
                    c_res.fill = fill_p2; c_res.font = font_p2
                elif sc == 1:
                    c_res.fill = fill_p1; c_res.font = font_p1
                elif sc == -1:
                    c_res.fill = fill_m1; c_res.font = font_m1
                elif sc == -2:
                    c_res.fill = fill_m2; c_res.font = font_m2
                else:
                    c_res.fill = fill_c0; c_res.font = font_c0
                col_eval += 1

            net = net_scores.get(alias, 0)
            c_bal = ws_team.cell(row=m_row, column=col_eval, value=f"{net:+d}")
            c_bal.font = font_bold; c_bal.alignment = align_center; c_bal.border = border_cell
            if net >= 3:
                c_bal.fill = fill_p2; c_bal.font = font_p2
            elif net > 0:
                c_bal.fill = fill_p1; c_bal.font = font_p1
            elif net <= -3:
                c_bal.fill = fill_m2; c_bal.font = font_m2
            elif net < 0:
                c_bal.fill = fill_m1; c_bal.font = font_m1
            else:
                c_bal.fill = fill_c0; c_bal.font = font_c0

            m_row += 1

        matrix_end_row = m_row - 1

        # ---------------------------------------------------------
        # BLOQUE B: ASISTENTE DE PAIRING DINÁMICO WTC
        # ---------------------------------------------------------
        rec_start_row = matrix_end_row + 2
        ws_team.cell(row=rec_start_row, column=1, value="🎛️ ASISTENTE DE PAIRING EN MESA (PANEL DE CONTROL WTC)").font = font_section_title

        curr_rec_row = rec_start_row + 1
        
        formula_rivales = '"' + ",".join(rival_nicks) + '"' if rival_nicks else '""'
        dv_rivals = DataValidation(type="list", formula1=formula_rivales, allow_blank=False)
        ws_team.add_data_validation(dv_rivals)

        formula_spears = '"' + ",".join(spears_names) + '"' if spears_names else '""'
        dv_spears = DataValidation(type="list", formula1=formula_spears, allow_blank=False)
        ws_team.add_data_validation(dv_spears)

        picked_spear_cell_refs = []
        picked_rival_cell_refs = []

        # Generar dinámicamente las S Tandas con numeración secuencial
        for k in range(num_shields):
            sh_num = k + 1
            sh_name = shields_names[k] if k < len(shields_names) else f"Escudo {sh_num}"
            fill_header_k = fill_tanda_headers[k % len(fill_tanda_headers)]
            
            step1_emoji = STEP_EMOJIS.get(3 * k + 1, f"[{3*k + 1}]")
            step2_emoji = STEP_EMOJIS.get(3 * k + 2, f"[{3*k + 2}]")
            step3_emoji = STEP_EMOJIS.get(3 * k + 3, f"[{3*k + 3}]")

            c_th = ws_team.cell(row=curr_rec_row, column=1, value=f"TANDA {sh_num} (Emparejamientos {2*k + 1} y {2*k + 2})")
            c_th.font = font_header; c_th.fill = fill_header_k

            ws_team.cell(row=curr_rec_row + 1, column=1, value=f"[OFERTA {sh_num}A] Su Defensor #{sh_num} -> Nuestras Lanzas").font = font_bold
            ws_team.cell(row=curr_rec_row + 1, column=3, value=f"[OFERTA {sh_num}B] Nuestro Escudo #{sh_num} ({sh_name}) -> Sus Atacantes").font = font_bold

            r_def_default = rival_nicks[k * 2] if (k * 2) < len(rival_nicks) else (rival_nicks[0] if rival_nicks else "")
            r_atk1_default = rival_nicks[k * 2 + 1] if (k * 2 + 1) < len(rival_nicks) else r_def_default

            r_def_row = curr_rec_row + 2
            ws_team.cell(row=r_def_row, column=1, value=f"{step1_emoji} Defensor Rival #{sh_num} revelado:").font = font_interactive
            c_r_def = ws_team.cell(row=r_def_row, column=2, value=r_def_default)
            c_r_def.font = font_bold; c_r_def.fill = fill_interactive_box; c_r_def.alignment = align_center; c_r_def.border = border_header
            dv_rivals.add(c_r_def)
            picked_rival_cell_refs.append(f"B{r_def_row}")

            ws_team.cell(row=r_def_row, column=3, value=f"• Atacante Rival #{sh_num}A para {sh_name}:").font = font_interactive
            c_r_atk1 = ws_team.cell(row=r_def_row, column=4, value=r_atk1_default)
            c_r_atk1.font = font_bold; c_r_atk1.fill = fill_interactive_box; c_r_atk1.alignment = align_center; c_r_atk1.border = border_header
            dv_rivals.add(c_r_atk1)

            r_atk2_default = rival_nicks[k * 2 + 2] if (k * 2 + 2) < len(rival_nicks) else r_atk1_default
            rec_spears_row = curr_rec_row + 3
            ws_team.cell(row=rec_spears_row, column=1, value=f"💡 Nuestras Lanzas recomendadas Tanda {sh_num}:").font = font_interactive
            
            if k == 0:
                spears_formula = build_spears_formula(f"B{r_def_row}", rival_best_spears)
            else:
                prev_pick = picked_spear_cell_refs[-1]
                if len(spears_names) == 3:
                    spears_formula = f'=IF({prev_pick}="{spears_names[0]}", "⚔️ {spears_names[1]} y {spears_names[2]}", IF({prev_pick}="{spears_names[1]}", "⚔️ {spears_names[0]} y {spears_names[2]}", "⚔️ {spears_names[0]} y {spears_names[1]}"))'
                else:
                    spears_formula = f'"⚔️ Lanzas activas restantes Tanda {sh_num}"'

            c_rec_sp = ws_team.cell(row=rec_spears_row, column=2, value=spears_formula)
            c_rec_sp.font = font_p1; c_rec_sp.fill = fill_p1; c_rec_sp.alignment = align_left; c_rec_sp.border = border_header

            ws_team.cell(row=rec_spears_row, column=3, value=f"• Atacante Rival #{sh_num}B para {sh_name}:").font = font_interactive
            c_r_atk2 = ws_team.cell(row=rec_spears_row, column=4, value=r_atk2_default)
            c_r_atk2.font = font_bold; c_r_atk2.fill = fill_interactive_box; c_r_atk2.alignment = align_center; c_r_atk2.border = border_header
            dv_rivals.add(c_r_atk2)

            pick_row = curr_rec_row + 4
            ws_team.cell(row=pick_row, column=1, value=f"{step2_emoji} ¿Qué Lanza aceptó el rival?:").font = font_interactive
            def_spear_pick = spears_names[min(k, len(spears_names) - 1)]
            c_sp_pick = ws_team.cell(row=pick_row, column=2, value=def_spear_pick)
            c_sp_pick.font = font_bold; c_sp_pick.fill = fill_interactive_box; c_sp_pick.alignment = align_center; c_sp_pick.border = border_header
            dv_spears.add(c_sp_pick)
            picked_spear_cell_refs.append(f"B{pick_row}")

            ws_team.cell(row=pick_row, column=3, value=f"💡 Recomendación para {sh_name}:").font = font_interactive
            rec_shield_formula = build_shield_rec_formula(sh_name, f"D{r_def_row}", f"D{rec_spears_row}", matrix.get(sh_name, {}), rival_nicks)
            c_rec_sh = ws_team.cell(row=pick_row, column=4, value=rec_shield_formula)
            c_rec_sh.font = font_p1; c_rec_sh.fill = fill_p1; c_rec_sh.alignment = align_left; c_rec_sh.border = border_header

            final_atk_row = curr_rec_row + 5
            ws_team.cell(row=final_atk_row, column=3, value=f"{step3_emoji} Atacante Rival aceptado para {sh_name}:").font = font_interactive
            c_atk_final = ws_team.cell(row=final_atk_row, column=4, value=r_atk1_default)
            c_atk_final.font = font_bold; c_atk_final.fill = fill_interactive_box; c_atk_final.alignment = align_center; c_atk_final.border = border_header
            dv_rivals.add(c_atk_final)
            picked_rival_cell_refs.append(f"D{final_atk_row}")

            for r_box in range(curr_rec_row, curr_rec_row + 6):
                for c_box in range(1, len(headers_matrix) + 1):
                    cb = ws_team.cell(row=r_box, column=c_box)
                    if cb.fill.fill_type is None:
                        cb.fill = fill_recommend_box
                    cb.border = border_cell

            curr_rec_row += 7

        # ---------------------------------------------------------
        # Cruce Final por Descarte (Cruce N)
        # ---------------------------------------------------------
        last_match_num = team_size
        c_cf_label = ws_team.cell(row=curr_rec_row, column=1, value=f"⚡ Cruce {last_match_num} (Automático por descarte final):")
        c_cf_label.font = font_section_title
        c_cf_label.fill = fill_recommend_box
        c_cf_label.border = border_header

        # Determinar rival restante dinámicamente con COUNTIF
        rival_checks = []
        for r_n in rival_nicks:
            # Revisa si este rival ya fue elegido en B{r_def_row} o D{final_atk_row}
            # Combinando las celdas de rivales
            conds = [f'{cell}="{r_n}"' for cell in picked_rival_cell_refs]
            or_cond = f'OR({", ".join(conds)})'
            rival_checks.append((r_n, or_cond))
            
        formula_rival_restante = f'"{rival_nicks[-1]}"'
        for r_n, cond in reversed(rival_checks[:-1]):
            formula_rival_restante = f'IF({cond}, {formula_rival_restante}, "{r_n}")'

        # Determinar lanza restante
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

        formula_cruce_completo = f'={formula_lanza_restante} & " vs " & {formula_rival_restante}'
        c_cf_val = ws_team.cell(row=curr_rec_row, column=2, value=formula_cruce_completo)
        c_cf_val.font = font_bold; c_cf_val.fill = fill_c0; c_cf_val.alignment = align_left; c_cf_val.border = border_header

        curr_rec_row += 3

        # ---------------------------------------------------------
        # BLOQUE C: LISTAS DETALLADAS DEL EQUIPO RIVAL
        # ---------------------------------------------------------
        list_start_row = curr_rec_row
        ws_team.cell(row=list_start_row, column=1, value="📋 LISTAS COMPLETAS DE INTEGRANTES DEL EQUIPO RIVAL").font = font_section_title

        header_row = list_start_row + 1
        faction_row = list_start_row + 2
        points_row = list_start_row + 3
        link_row = list_start_row + 4
        content_row = list_start_row + 5

        for col_idx, p_data in enumerate(players_data, 1):
            p_name = p_data.get('player_name', 'Jugador')
            faction = p_data.get('faction', 'Sin Facción')
            points = p_data.get('points', '')
            list_lines = p_data.get('list_lines', [])
            raw_xws = p_data.get('raw_xws', '')

            yasb_link = ""
            if raw_xws:
                try:
                    js_x = json.loads(raw_xws)
                    yasb_link = js_x.get('vendor', {}).get('yasb', {}).get('link') or js_x.get('vendor', {}).get('lbn', {}).get('link') or ""
                except Exception:
                    pass

            c_name = ws_team.cell(row=header_row, column=col_idx, value=p_name)
            c_name.font = font_player_header; c_name.fill = fill_player_header; c_name.alignment = align_center; c_name.border = border_header

            c_fac = ws_team.cell(row=faction_row, column=col_idx, value=f"Facción: {faction}" if faction else "")
            c_fac.font = font_faction; c_fac.fill = fill_card_content; c_fac.alignment = align_center; c_fac.border = border_cell

            c_pts = ws_team.cell(row=points_row, column=col_idx, value=f"Total: {points}" if points else "")
            c_pts.font = font_points; c_pts.fill = fill_card_content; c_pts.alignment = align_center; c_pts.border = border_cell

            c_link = ws_team.cell(row=link_row, column=col_idx)
            if yasb_link:
                c_link.value = "🔗 Abrir lista en YASB"
                c_link.hyperlink = yasb_link
                c_link.font = font_link
            else:
                c_link.value = ""
                c_link.font = font_normal
            c_link.fill = fill_card_content; c_link.alignment = align_center; c_link.border = border_cell

            full_list_text = "\n".join(list_lines) if list_lines else "Sin lista registrada"
            c_list = ws_team.cell(row=content_row, column=col_idx, value=full_list_text)
            c_list.font = font_normal; c_list.fill = fill_card_content; c_list.alignment = align_top_left; c_list.border = border_cell

            col_letter = get_column_letter(col_idx)
            ws_team.column_dimensions[col_letter].width = 44

        ws_team.column_dimensions['A'].width = 16
        ws_team.column_dimensions['B'].width = 32
        ws_team.column_dimensions['C'].width = 24
        for c_i in range(4, len(headers_matrix) + 1):
            ws_team.column_dimensions[get_column_letter(c_i)].width = 20

    try:
        wb.save(output_filename)
        print(f"[+] Libro Excel adaptable ({team_size} jugadores) guardado en: {output_filename}")
        return output_filename
    except PermissionError:
        alt_filename = output_filename.replace('.xlsx', '_nuevo.xlsx')
        try:
            wb.save(alt_filename)
            print(f"[!] AVISO: '{os.path.basename(output_filename)}' está actualmente abierto en Excel.")
            print(f"[+] Se ha guardado una copia actualizada en: {alt_filename}")
            return alt_filename
        except Exception:
            raise PermissionError(
                f"No se pudo guardar '{output_filename}' porque está abierto en Excel.\n"
                "Por favor, cierra el archivo en Excel e inténtalo de nuevo."
            )
