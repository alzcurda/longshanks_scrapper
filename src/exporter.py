import re
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from src.config import OUTPUT_DIR
from src.matrix_evaluator import evaluate_5x5_matrix

def sanitize_sheet_title(name: str) -> str:
    """Limpia y trunca el nombre de un equipo para que sea un título válido de pestaña en Excel (máx 31 caracteres)."""
    if not name:
        return "Equipo Sin Nombre"
    clean_name = re.sub(r'[\\/*?:\[\]]', '', name).strip()
    return clean_name[:31] if clean_name else "Equipo"

def build_nested_if_formula_tanda1(drop_cell_ref: str, rival_best_map: dict) -> str:
    """Construye una fórmula anidada IF(...) universal para la Tanda 1."""
    items = list(rival_best_map.items())
    if not items:
        return '"No disponible"'
        
    formula = f'"⚔️ {items[-1][1]}"'
    for r_nick, best_atks in reversed(items[:-1]):
        formula = f'IF({drop_cell_ref}="{r_nick}", "⚔️ {best_atks}", {formula})'
        
    return "=" + formula

def export_to_excel(event_id: str, event_data: dict, output_filename: str = None) -> str:
    """
    Genera un libro de Excel (.xlsx) interactivo con el ASISTENTE BIDIRECCIONAL COMPLETO WTC:
    - Criterio de Sacrificio WTC: Si dos Lanzas empatan contra un defensor rival, se ofrece a la Lanza con MENOS verdes globales (sacrificado) para RESERVAR a la Lanza con MÁS verdes globales para la Tanda 2.
    """
    if not output_filename:
        output_filename = os.path.join(OUTPUT_DIR, f"event_{event_id}_listas.xlsx")
    elif not os.path.isabs(output_filename):
        output_filename = os.path.join(OUTPUT_DIR, output_filename)

    wb = openpyxl.Workbook()
    
    # Estilos de Excel
    font_title = Font(name='Segoe UI', size=14, bold=True, color='1F4E78')
    font_section_title = Font(name='Segoe UI', size=12, bold=True, color='1F4E78')
    font_header = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
    font_player_header = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
    font_faction = Font(name='Segoe UI', size=10, italic=True, color='595959')
    font_points = Font(name='Segoe UI', size=10, bold=True, color='2F5597')
    font_normal = Font(name='Segoe UI', size=10)
    font_bold = Font(name='Segoe UI', size=10, bold=True)
    font_interactive = Font(name='Segoe UI', size=10, bold=True, color='1F4E78')
    
    font_green = Font(name='Segoe UI', size=10, bold=True, color='276A3C')
    font_yellow = Font(name='Segoe UI', size=10, bold=True, color='B25900')
    font_red = Font(name='Segoe UI', size=10, bold=True, color='9C0006')
    
    fill_team_header = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    fill_player_header = PatternFill(start_color='2F5597', end_color='2F5597', fill_type='solid')
    fill_matrix_header = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    fill_tanda1_header = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
    fill_tanda2_header = PatternFill(start_color='C55A11', end_color='C55A11', fill_type='solid')
    fill_recommend_box = PatternFill(start_color='E9EEF4', end_color='E9EEF4', fill_type='solid')
    fill_interactive_box = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    fill_zebra = PatternFill(start_color='F2F4F8', end_color='F2F4F8', fill_type='solid')
    
    fill_green = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    fill_yellow = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
    fill_red = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    
    thin_side = Side(border_style="thin", color="D9D9D9")
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
    
    ws_summary.cell(row=1, column=1, value=f"Longshanks Event #{event_id} - Resumen por Equipos").font = font_title
    
    headers_summary = ["Equipo", "ID Jugador", "Jugador / Nick", "Facción", "Puntos"]
    for col_num, h_text in enumerate(headers_summary, 1):
        cell = ws_summary.cell(row=3, column=col_num, value=h_text)
        cell.font = font_header
        cell.fill = fill_team_header
        cell.alignment = align_center
        cell.border = border_header
        
    current_row = 4
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
                if current_row % 2 == 0:
                    c.fill = fill_zebra
            current_row += 1
            
    for col in ws_summary.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_summary.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # -------------------------------------------------------------
    # Pestañas por Cada Equipo
    # -------------------------------------------------------------
    used_titles = set()
    mudhorns_info = [
        ("Alzu", "Rebeldes (Defensor #1 Fijo)"),
        ("Ander", "Separatistas (Defensor #2 Fijo)"),
        ("Marc", "Primera Orden (Lanza)"),
        ("Koli", "República (Lanza)"),
        ("Ale", "Scum (Lanza)")
    ]
    lanzas_list = ["Marc", "Koli", "Ale"]
    
    for team in event_data.get('teams', []):
        t_name = team.get('team_name', 'Equipo')
        sheet_title = sanitize_sheet_title(t_name)
        
        base_title = sheet_title
        counter = 1
        while sheet_title in used_titles:
            suffix = f" ({counter})"
            sheet_title = base_title[:31 - len(suffix)] + suffix
            counter += 1
        used_titles.add(sheet_title)
        
        ws_team = wb.create_sheet(title=sheet_title)
        ws_team.views.sheetView[0].showGridLines = True
        
        ws_team.cell(row=1, column=1, value=f"Equipo Rival: {t_name}").font = font_title
        
        players_data = team.get('players_data', [])
        if not players_data:
            ws_team.cell(row=3, column=1, value="No se encontraron datos para este equipo.").font = font_normal
            continue

        lanzas_global_net = {m: 0 for m in lanzas_list}
        for p_data in players_data:
            eval_matrix = evaluate_5x5_matrix(p_data)
            for m in lanzas_list:
                lanzas_global_net[m] += eval_matrix.get(m, {}).get('score', 0)

        # ---------------------------------------------------------
        # BLOQUE A: MATRIZ DE EMPAREJAMIENTOS 5x5 TRANSPUESTA
        # ---------------------------------------------------------
        ws_team.cell(row=3, column=1, value="🎯 MATRIZ DE EMPAREJAMIENTOS 5x5 (Iberian Mudhorns vs Rival)").font = font_section_title
        
        headers_matrix = ["Jugador Mudhorn", "Perfil / Rol"]
        rival_nicks = []
        rival_best_tanda1 = {}

        for p_data in players_data:
            r_nick = p_data.get('player_name', 'Rival')
            rival_nicks.append(r_nick)
            headers_matrix.append(f"vs {r_nick}")
            
            eval_matrix = evaluate_5x5_matrix(p_data)
            
            # Criterio táctico WTC:
            # 1. Mayor puntuación específica contra este defensor rival.
            # 2. Desempate: Menor puntaje global (sacrificar al que tiene MENOS verdes y RESERVAR al que tiene MÁS verdes para la Tanda 2).
            lanzas1 = []
            for m_name in lanzas_list:
                spec_score = eval_matrix.get(m_name, {}).get('score', 0)
                glob_score = lanzas_global_net[m_name]
                lanzas1.append((m_name, spec_score, glob_score))
                
            # Ordenar por spec_score DESCENDENTE (x[1]), y desempate glob_score ASCENDENTE (x[2])
            lanzas1.sort(key=lambda x: (x[1], -x[2]), reverse=True)
            
            best_two_names = sorted([lanzas1[0][0], lanzas1[1][0]])
            rival_best_tanda1[r_nick] = f"{best_two_names[0]} y {best_two_names[1]}"

        headers_matrix.append("Balance Net Score")
        
        for col_idx, h_text in enumerate(headers_matrix, 1):
            c = ws_team.cell(row=4, column=col_idx, value=h_text)
            c.font = font_header
            c.fill = fill_matrix_header
            c.alignment = align_center
            c.border = border_header
            
        m_row = 5
        for m_name, m_role in mudhorns_info:
            c_name = ws_team.cell(row=m_row, column=1, value=m_name)
            c_name.font = font_bold
            c_name.border = border_cell
            
            c_role = ws_team.cell(row=m_row, column=2, value=m_role)
            c_role.font = font_faction
            c_role.border = border_cell
            
            net_score = 0
            for col_idx, p_data in enumerate(players_data, 3):
                eval_matrix = evaluate_5x5_matrix(p_data)
                eval_info = eval_matrix.get(m_name, {'score': 0, 'symbol': '🟡', 'reason': ''})
                score = eval_info['score']
                symbol = eval_info['symbol']
                net_score += score
                
                c_eval = ws_team.cell(row=m_row, column=col_idx, value=f"{symbol} ({score:+d})")
                c_eval.alignment = align_center
                c_eval.border = border_cell
                
                if score > 0:
                    c_eval.fill = fill_green
                    c_eval.font = font_green
                elif score < 0:
                    c_eval.fill = fill_red
                    c_eval.font = font_red
                else:
                    c_eval.fill = fill_yellow
                    c_eval.font = font_yellow
                    
            bal_col = len(players_data) + 3
            c_bal = ws_team.cell(row=m_row, column=bal_col, value=f"{net_score:+d}")
            c_bal.font = font_bold
            c_bal.alignment = align_center
            c_bal.border = border_cell
            if net_score > 0:
                c_bal.fill = fill_green
                c_bal.font = font_green
            elif net_score < 0:
                c_bal.fill = fill_red
                c_bal.font = font_red
            else:
                c_bal.fill = fill_yellow
                c_bal.font = font_yellow
                
            m_row += 1

        # ---------------------------------------------------------
        # BLOQUE B: ASISTENTE COMPACTO WTC (LAYOUT SIN GAPS)
        # ---------------------------------------------------------
        r0 = rival_nicks[0] if len(rival_nicks) > 0 else ""
        r1 = rival_nicks[1] if len(rival_nicks) > 1 else r0
        r2 = rival_nicks[2] if len(rival_nicks) > 2 else r0
        r3 = rival_nicks[3] if len(rival_nicks) > 3 else r0
        r4 = rival_nicks[4] if len(rival_nicks) > 4 else r0

        rec_start_row = 11
        ws_team.cell(row=rec_start_row, column=1, value="🎛️ ASISTENTE DE PAIRING COMPACTO (PANEL CONTROL WTC EN MESA)").font = font_section_title
        
        # --- TANDA 1 ---
        ws_team.cell(row=rec_start_row + 1, column=1, value="🔵 TANDA 1 (Primeros 2 Emparejamientos)").font = font_header
        ws_team.cell(row=rec_start_row + 1, column=1).fill = fill_tanda1_header

        ws_team.cell(row=rec_start_row + 2, column=1, value="[OFERTA 1A] Su Defensor -> Nuestras Lanzas").font = font_bold
        ws_team.cell(row=rec_start_row + 2, column=3, value="[OFERTA 1B] Nuestro Defensor #1 Alzu -> Sus Atacantes").font = font_bold
        
        ws_team.cell(row=14, column=1, value="1️⃣ Defensor Rival #1 revelado:").font = font_interactive
        c_r1_def = ws_team.cell(row=14, column=2, value=r0)
        c_r1_def.font = font_bold; c_r1_def.fill = fill_interactive_box; c_r1_def.alignment = align_center; c_r1_def.border = border_header

        ws_team.cell(row=14, column=3, value="• Atacante Rival #1A para Alzu:").font = font_interactive
        c_r1_atk1 = ws_team.cell(row=14, column=4, value=r1)
        c_r1_atk1.font = font_bold; c_r1_atk1.fill = fill_interactive_box; c_r1_atk1.alignment = align_center; c_r1_atk1.border = border_header

        ws_team.cell(row=15, column=1, value="💡 Nuestras 2 Lanzas recomendadas:").font = font_interactive
        c_rec_lanzas1 = ws_team.cell(row=15, column=2, value=build_nested_if_formula_tanda1("B14", rival_best_tanda1))
        c_rec_lanzas1.font = font_green; c_rec_lanzas1.fill = fill_green; c_rec_lanzas1.alignment = align_left; c_rec_lanzas1.border = border_header

        ws_team.cell(row=15, column=3, value="• Atacante Rival #1B para Alzu:").font = font_interactive
        c_r1_atk2 = ws_team.cell(row=15, column=4, value=r2)
        c_r1_atk2.font = font_bold; c_r1_atk2.fill = fill_interactive_box; c_r1_atk2.alignment = align_center; c_r1_atk2.border = border_header

        ws_team.cell(row=16, column=1, value="2️⃣ ¿Qué Lanza aceptó el rival?:").font = font_interactive
        c_m_lan1_pick = ws_team.cell(row=16, column=2, value="Koli")
        c_m_lan1_pick.font = font_bold; c_m_lan1_pick.fill = fill_interactive_box; c_m_lan1_pick.alignment = align_center; c_m_lan1_pick.border = border_header

        ws_team.cell(row=16, column=3, value="💡 Recomendación para Alzu:").font = font_interactive
        c_rec_alzu = ws_team.cell(row=16, column=4, value='=IF(D14="", "Esperando asignación", "🛡️ Recomendado: " & D14)')
        c_rec_alzu.font = font_green; c_rec_alzu.fill = fill_green; c_rec_alzu.alignment = align_left; c_rec_alzu.border = border_header

        ws_team.cell(row=17, column=3, value="3️⃣ Atacante Rival aceptado para Alzu:").font = font_interactive
        c_r_atk1_final = ws_team.cell(row=17, column=4, value=r1)
        c_r_atk1_final.font = font_bold; c_r_atk1_final.fill = fill_interactive_box; c_r_atk1_final.alignment = align_center; c_r_atk1_final.border = border_header

        # --- TANDA 2 ---
        ws_team.cell(row=19, column=1, value="🔴 TANDA 2 (Emparejamientos 3, 4 y 5)").font = font_header
        ws_team.cell(row=19, column=1).fill = fill_tanda2_header

        ws_team.cell(row=20, column=1, value="[OFERTA 2A] Su Defensor #2 -> Lanzas Restantes").font = font_bold
        ws_team.cell(row=20, column=3, value="[OFERTA 2B] Nuestro Defensor #2 Ander -> Sus Atacantes").font = font_bold

        ws_team.cell(row=21, column=1, value="4️⃣ Defensor Rival #2 revelado:").font = font_interactive
        c_r2_def = ws_team.cell(row=21, column=2, value=r3)
        c_r2_def.font = font_bold; c_r2_def.fill = fill_interactive_box; c_r2_def.alignment = align_center; c_r2_def.border = border_header

        ws_team.cell(row=21, column=3, value="• Atacante Rival #2A para Ander:").font = font_interactive
        c_r2_atk1 = ws_team.cell(row=21, column=4, value=r3)
        c_r2_atk1.font = font_bold; c_r2_atk1.fill = fill_interactive_box; c_r2_atk1.alignment = align_center; c_r2_atk1.border = border_header

        ws_team.cell(row=22, column=1, value="💡 Lanzas disponibles Tanda 2:").font = font_interactive
        c_rec_lanzas2 = ws_team.cell(row=22, column=2, value='=IF(B16="Marc", "⚔️ Koli y Ale", IF(B16="Koli", "⚔️ Marc y Ale", "⚔️ Marc y Koli"))')
        c_rec_lanzas2.font = font_green; c_rec_lanzas2.fill = fill_green; c_rec_lanzas2.alignment = align_left; c_rec_lanzas2.border = border_header

        ws_team.cell(row=22, column=3, value="• Atacante Rival #2B para Ander:").font = font_interactive
        c_r2_atk2 = ws_team.cell(row=22, column=4, value=r4)
        c_r2_atk2.font = font_bold; c_r2_atk2.fill = fill_interactive_box; c_r2_atk2.alignment = align_center; c_r2_atk2.border = border_header

        ws_team.cell(row=23, column=1, value="5️⃣ ¿Qué Lanza aceptó el rival?:").font = font_interactive
        c_m_lan2_pick = ws_team.cell(row=23, column=2, value="Marc")
        c_m_lan2_pick.font = font_bold; c_m_lan2_pick.fill = fill_interactive_box; c_m_lan2_pick.alignment = align_center; c_m_lan2_pick.border = border_header

        ws_team.cell(row=23, column=3, value="💡 Recomendación para Ander:").font = font_interactive
        c_rec_ander = ws_team.cell(row=23, column=4, value='=IF(D21="", "Esperando asignación", "🛡️ Recomendado: " & D21)')
        c_rec_ander.font = font_green; c_rec_ander.fill = fill_green; c_rec_ander.alignment = align_left; c_rec_ander.border = border_header

        ws_team.cell(row=24, column=3, value="6️⃣ Atacante Rival aceptado para Ander:").font = font_interactive
        c_r_atk2_final = ws_team.cell(row=24, column=4, value=r3)
        c_r_atk2_final.font = font_bold; c_r_atk2_final.fill = fill_interactive_box; c_r_atk2_final.alignment = align_center; c_r_atk2_final.border = border_header

        ws_team.cell(row=26, column=1, value="⚡ Cruce 5 (Automático por descarte final):").font = font_section_title
        formula_cruce5 = f'=IF(AND(B16<>"Marc", B23<>"Marc"), "⚔️ Marc", IF(AND(B16<>"Koli", B23<>"Koli"), "⚔️ Koli", "⚔️ Ale")) & " vs " & IF(AND(D17<>"{r1}", D24<>"{r1}"), "{r1}", "{r4}")'
        c_cruce5 = ws_team.cell(row=26, column=2, value=formula_cruce5)
        c_cruce5.font = font_bold; c_cruce5.fill = fill_yellow; c_cruce5.alignment = align_left; c_cruce5.border = border_header

        if rival_nicks:
            formula_rivales = '"' + ",".join(rival_nicks) + '"'
            dv_r = DataValidation(type="list", formula1=formula_rivales, allow_blank=False)
            ws_team.add_data_validation(dv_r)
            dv_r.add(c_r1_def); dv_r.add(c_r1_atk1); dv_r.add(c_r1_atk2); dv_r.add(c_r_atk1_final)
            dv_r.add(c_r2_def); dv_r.add(c_r2_atk1); dv_r.add(c_r2_atk2); dv_r.add(c_r_atk2_final)

        formula_lanzas = '"Marc,Koli,Ale"'
        dv_l = DataValidation(type="list", formula1=formula_lanzas, allow_blank=False)
        ws_team.add_data_validation(dv_l)
        dv_l.add(c_m_lan1_pick); dv_l.add(c_m_lan2_pick)

        for r_idx in range(12, 27):
            for c_idx in range(1, len(headers_matrix) + 1):
                cell_box = ws_team.cell(row=r_idx, column=c_idx)
                if not cell_box.fill.start_color.rgb:
                    cell_box.fill = fill_recommend_box
                cell_box.border = border_cell

        # ---------------------------------------------------------
        # BLOQUE C: LISTAS DETALLADAS DEL EQUIPO RIVAL (Rows 29+)
        # ---------------------------------------------------------
        list_start_row = 29
        ws_team.cell(row=list_start_row, column=1, value="📋 LISTAS COMPLETAS DE INTEGRANTES DEL EQUIPO RIVAL").font = font_section_title
        
        header_row = list_start_row + 1
        faction_row = list_start_row + 2
        points_row = list_start_row + 3
        content_row = list_start_row + 4

        for col_idx, p_data in enumerate(players_data, 1):
            p_name = p_data.get('player_name', 'Jugador')
            faction = p_data.get('faction', 'Sin Facción')
            points = p_data.get('points', '')
            list_lines = p_data.get('list_lines', [])
            
            c_name = ws_team.cell(row=header_row, column=col_idx, value=p_name)
            c_name.font = font_player_header
            c_name.fill = fill_player_header
            c_name.alignment = align_center
            c_name.border = border_header
            
            c_fac = ws_team.cell(row=faction_row, column=col_idx, value=f"Facción: {faction}" if faction else "")
            c_fac.font = font_faction
            c_fac.alignment = align_center
            c_fac.border = border_cell
            
            c_pts = ws_team.cell(row=points_row, column=col_idx, value=f"Total: {points}" if points else "")
            c_pts.font = font_points
            c_pts.alignment = align_center
            c_pts.border = border_cell
            
            full_list_text = "\n".join(list_lines) if list_lines else "Sin lista registrada"
            c_list = ws_team.cell(row=content_row, column=col_idx, value=full_list_text)
            c_list.font = font_normal
            c_list.alignment = align_top_left
            c_list.border = border_cell
            
            col_letter = get_column_letter(col_idx)
            ws_team.column_dimensions[col_letter].width = 44

    wb.save(output_filename)
    print(f"[+] Libro Excel con criterio de sacrificio WTC guardado en: {output_filename}")
    return output_filename
