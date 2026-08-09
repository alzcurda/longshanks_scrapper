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
    Genera un libro de Excel (.xlsx) con el ASISTENTE DINÁMICO COMPLETO WTC:
    - Defensores Fijos Únicos: Alzu (Defensor 1) y Ander (Defensor 2).
    - Lanzas Disponibles: Marc, Koli, Ale.
    - Tanda 1: Elección de Defensor Rival + Elección de Lanza aceptada.
    - Tanda 2: Actualización dinámica de Lanzas restantes + Elección Lanza Tanda 2.
    - Cruce 5: Cálculo automático de la Lanza descartada que juega el Cruce 5.
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
    font_interactive = Font(name='Segoe UI', size=11, bold=True, color='1F4E78')
    
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
    # Pestañas por Cada Equipo (Dashboard 5x5 + Flujo Dinámico WTC)
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
            
            # Buscar las 2 mejores lanzas (entre Marc, Koli, Ale) contra este rival
            lanzas1 = []
            for m_name in lanzas_list:
                lanzas1.append((m_name, eval_matrix.get(m_name, {}).get('score', 0)))
            lanzas1.sort(key=lambda x: -x[1])
            rival_best_tanda1[r_nick] = f"{lanzas1[0][0]} y {lanzas1[1][0]}"

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
        # BLOQUE B: ASISTENTE DINÁMICO DE PAIRINGS (FLUJO 2 TANDAS WTC)
        # ---------------------------------------------------------
        rec_start_row = 11
        ws_team.cell(row=rec_start_row, column=1, value="🎛️ ASISTENTE INTERACTIVO DE PAIRINGS (FLUJO COMPLETO WTC EN TIEMPO REAL)").font = font_section_title
        
        # --- TANDA 1 ---
        ws_team.cell(row=rec_start_row + 1, column=1, value="🔵 TANDA 1 (Primeros 2 Emparejamientos)").font = font_header
        ws_team.cell(row=rec_start_row + 1, column=1).fill = fill_tanda1_header
        
        ws_team.cell(row=rec_start_row + 2, column=1, value="• Defensor #1 Presentado (a ciegas): Alzu (Rebeldes)").font = font_bold
        
        # 1. Desplegable Defensor Rival #1 (C14)
        c_drop1_label = ws_team.cell(row=rec_start_row + 3, column=1, value="1️⃣ Selecciona el Defensor Rival #1 revelado (Tanda 1):")
        c_drop1_label.font = font_interactive
        
        c_drop1 = ws_team.cell(row=rec_start_row + 3, column=3, value=rival_nicks[0] if rival_nicks else "")
        c_drop1.font = font_bold
        c_drop1.fill = fill_interactive_box
        c_drop1.alignment = align_center
        c_drop1.border = border_header

        # Respuesta 1 (C15): Recomendación de 2 Lanzas
        c_resp1_label = ws_team.cell(row=rec_start_row + 4, column=1, value="💡 ATACANTES RECOMENDADOS A OFRECERLE:")
        c_resp1_label.font = font_interactive
        
        formula_tanda1 = build_nested_if_formula_tanda1("C14", rival_best_tanda1)
        c_resp1 = ws_team.cell(row=rec_start_row + 4, column=3, value=formula_tanda1)
        c_resp1.font = font_green
        c_resp1.fill = fill_green
        c_resp1.alignment = align_left
        c_resp1.border = border_header

        # 2. Desplegable Lanza elegida por Rival en Tanda 1 (C16)
        c_pick1_label = ws_team.cell(row=rec_start_row + 5, column=1, value="2️⃣ ¿Qué Lanza de vuestras 2 ofreció/aceptó el rival en Tanda 1?:")
        c_pick1_label.font = font_interactive
        
        c_pick1 = ws_team.cell(row=rec_start_row + 5, column=3, value="Marc")
        c_pick1.font = font_bold
        c_pick1.fill = fill_interactive_box
        c_pick1.alignment = align_center
        c_pick1.border = border_header

        # --- TANDA 2 ---
        ws_team.cell(row=rec_start_row + 7, column=1, value="🔴 TANDA 2 (Emparejamientos 3, 4 y 5)").font = font_header
        ws_team.cell(row=rec_start_row + 7, column=1).fill = fill_tanda2_header
        
        ws_team.cell(row=rec_start_row + 8, column=1, value="• Defensor #2 Presentado (a ciegas): Ander (Separatistas)").font = font_bold

        # 3. Desplegable Defensor Rival #2 (C20)
        c_drop2_label = ws_team.cell(row=rec_start_row + 9, column=1, value="3️⃣ Selecciona el Defensor Rival #2 revelado (Tanda 2):")
        c_drop2_label.font = font_interactive
        
        c_drop2 = ws_team.cell(row=rec_start_row + 9, column=3, value=rival_nicks[1] if len(rival_nicks) > 1 else (rival_nicks[0] if rival_nicks else ""))
        c_drop2.font = font_bold
        c_drop2.fill = fill_interactive_box
        c_drop2.alignment = align_center
        c_drop2.border = border_header

        # Respuesta Tanda 2 (C21): Dinámica según la Lanza elegida en C16
        c_resp2_label = ws_team.cell(row=rec_start_row + 10, column=1, value="💡 LAS 2 LANZAS RESTANTES A OFRECERLE EN TANDA 2:")
        c_resp2_label.font = font_interactive
        
        formula_tanda2 = '=IF(C16="Marc", "⚔️ Koli y Ale", IF(C16="Koli", "⚔️ Marc y Ale", "⚔️ Marc y Koli"))'
        c_resp2 = ws_team.cell(row=rec_start_row + 10, column=3, value=formula_tanda2)
        c_resp2.font = font_green
        c_resp2.fill = fill_green
        c_resp2.alignment = align_left
        c_resp2.border = border_header

        # 4. Desplegable Lanza elegida por Rival en Tanda 2 (C22)
        c_pick2_label = ws_team.cell(row=rec_start_row + 11, column=1, value="4️⃣ ¿Qué Lanza aceptó el rival en Tanda 2?:")
        c_pick2_label.font = font_interactive
        
        c_pick2 = ws_team.cell(row=rec_start_row + 11, column=3, value="Koli")
        c_pick2.font = font_bold
        c_pick2.fill = fill_interactive_box
        c_pick2.alignment = align_center
        c_pick2.border = border_header

        # 5. Cruce 5 Automático por Descarte Final (C23)
        c_cruce5_label = ws_team.cell(row=rec_start_row + 12, column=1, value="⚡ Cruce 5 (Automático por descarte final):")
        c_cruce5_label.font = font_interactive
        
        formula_cruce5 = '=IF(AND(C16<>"Marc", C22<>"Marc"), "⚔️ Marc (Nuestra Lanza descartada)", IF(AND(C16<>"Koli", C22<>"Koli"), "⚔️ Koli (Nuestra Lanza descartada)", "⚔️ Ale (Nuestra Lanza descartada)"))'
        c_cruce5 = ws_team.cell(row=rec_start_row + 12, column=3, value=formula_cruce5)
        c_cruce5.font = font_bold
        c_cruce5.fill = fill_yellow
        c_cruce5.alignment = align_left
        c_cruce5.border = border_header

        # Aplicar DataValidation a los desplegables
        if rival_nicks:
            formula_rivales = '"' + ",".join(rival_nicks) + '"'
            dv_rival1 = DataValidation(type="list", formula1=formula_rivales, allow_blank=False)
            ws_team.add_data_validation(dv_rival1)
            dv_rival1.add(c_drop1)
            
            dv_rival2 = DataValidation(type="list", formula1=formula_rivales, allow_blank=False)
            ws_team.add_data_validation(dv_rival2)
            dv_rival2.add(c_drop2)

        formula_lanzas = '"Marc,Koli,Ale"'
        dv_lan1 = DataValidation(type="list", formula1=formula_lanzas, allow_blank=False)
        ws_team.add_data_validation(dv_lan1)
        dv_lan1.add(c_pick1)
        
        dv_lan2 = DataValidation(type="list", formula1=formula_lanzas, allow_blank=False)
        ws_team.add_data_validation(dv_lan2)
        dv_lan2.add(c_pick2)

        # Aplicar estilos de bordes y relleno al bloque del asistente
        for r_offset in range(1, 13):
            r_idx = rec_start_row + r_offset
            for c_idx in range(1, len(headers_matrix) + 1):
                cell_box = ws_team.cell(row=r_idx, column=c_idx)
                if not cell_box.fill.start_color.rgb:
                    cell_box.fill = fill_recommend_box
                cell_box.border = border_cell

        # ---------------------------------------------------------
        # BLOQUE C: LISTAS DETALLADAS DEL EQUIPO RIVAL (Rows 26+)
        # ---------------------------------------------------------
        list_start_row = 26
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
    print(f"[+] Libro Excel con Asistente Dinámico WTC guardado en: {output_filename}")
    return output_filename
