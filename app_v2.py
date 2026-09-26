import streamlit as st
import database_v2 as db_v2
from music_engine import generate_midi, generate_preview_midi
from ui_components import render_midi_player, render_virtual_keyboard
db = db_v2.load_db()

def clean_edit_cache():
    for key in ["in_ed_name", "in_ed_pat"]:
        if key in st.session_state: del st.session_state[key]

# ==============================
# LÓGICA DE FILTRADO
# ==============================
user_playlists = [p for p in db["playlists"] if p != "Archivar"]
all_filters = ["Todas"] + user_playlists + ["📦 Archivados"]

if "widget_filter" not in st.session_state:
    st.session_state.widget_filter = db.get("last_selected_filter", "Todas")
    if st.session_state.widget_filter not in all_filters: st.session_state.widget_filter = "Todas"

def update_filter():
    db_v2.update_pref_filter(st.session_state.widget_filter)
    clean_edit_cache()

# Dividimos la parte superior para hacer espacio al botón de sincronizar
col_top1, col_top2 = st.columns([8, 2])

with col_top1:
    with st.popover(f"📂 Carpeta: {st.session_state.widget_filter}", use_container_width=True):
        st.radio("Selecciona carpeta:", all_filters, key="widget_filter", on_change=update_filter, label_visibility="collapsed")

with col_top2:
    if st.button("🔄", help="Sincronizar BD (Traer cambios de otros dispositivos)", use_container_width=True):
        db_v2.load_db.clear()  # <--- Este es el comando directo de Streamlit
        st.rerun()

current_filter = st.session_state.widget_filter

if current_filter == "Todas": 
    available_exs = sorted([name for name, d in db["exercises"].items() if "Archivar" not in d["playlists"]])
elif current_filter == "📦 Archivados": 
    available_exs = sorted([name for name, d in db["exercises"].items() if "Archivar" in d["playlists"]])
else: 
    available_exs = sorted([name for name, d in db["exercises"].items() if current_filter in d["playlists"] and "Archivar" not in d["playlists"]])

if not available_exs:
    st.info(f"No hay ejercicios en la categoría '{current_filter}'.")
    st.stop()
    
if "widget_selector" not in st.session_state or st.session_state.widget_selector not in available_exs:
    last_ex = db.get("last_selected_exercise")
    st.session_state.widget_selector = last_ex if last_ex in available_exs else available_exs[0]
    db_v2.update_pref_exercise(st.session_state.widget_selector)

def sync_selection():
    selected = st.session_state.get("widget_selector")
    if selected:
        db_v2.update_pref_exercise(selected)
        clean_edit_cache()

with st.popover(f"🎵 Ejercicio: {st.session_state.widget_selector}", use_container_width=True):
    exercise = st.radio("Selecciona el ejercicio", options=available_exs, key="widget_selector", on_change=sync_selection, label_visibility="collapsed")

st.session_state.selected_ex = exercise

# ==============================
# TRADUCTORES DE PATRÓN (Texto <-> Tabla)
# ==============================
def parse_pattern_to_list(pat):
    res = []
    for token in pat.replace(" ", "").split(","):
        if not token: continue
        dur = 1.0
        if "[x" in token:
            try:
                base, d_str = token.split("[x")
                dur = float(d_str[:-1])
                token = base
            except: pass
        
        alt = ""
        if token.endswith("b"): alt = "b"; token = token[:-1]
        elif token.endswith("#"): alt = "#"; token = token[:-1]
        
        nota = "R" if token.upper() in ["R", "0"] else token
        res.append({"Nota": nota, "Alt": alt, "Dur": dur})
    
    if not res: res = [{"Nota": "1", "Alt": "", "Dur": 1.0}]
    return res

def list_to_pattern(lst):
    tokens = []
    for row in lst:
        n = str(row.get("Nota", "1")).strip()
        base = "R" if n.upper() == "R" else f"{n}{row.get('Alt', '')}"
        try: dur = float(row.get("Dur", 1.0))
        except: dur = 1.0
        
        if dur == 1.0: tokens.append(base)
        else: tokens.append(f"{base}[x{dur:g}]")
    return ", ".join(tokens)

# ==============================
# MENÚS ADMINISTRACIÓN
# ==============================
col_admin1, col_admin2 = st.columns(2)

with col_admin1:
    with st.popover("🛠️ Modificar BD", use_container_width=True):
        tab_edit, tab_new, tab_del, tab_order, tab_import = st.tabs(["✏️ Editar", "➕ Crear", "🗑️ Borrar", "🔄 Ordenar", "📥 Importar"])

        with tab_edit:
            edit_name = st.text_input("Nombre:", value=exercise)
            current_db_pat = db["exercises"][exercise]["pattern"]
            
            with st.expander("🎹 Abrir Teclado Virtual (Constructor)"):
                render_virtual_keyboard(current_db_pat)
            
            edit_pat = st.text_area("Código del Patrón:", value=current_db_pat, height=120)
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if st.button("▶️ Preview", use_container_width=True, key="prev_edit"):
                    try:
                        prev_uri = generate_preview_midi(edit_pat, stgs.get("bpm", 120))
                        render_midi_player(prev_uri)
                    except Exception: st.error("Error en patrón")
            with col_p2:
                if st.button("💾 Guardar", type="primary", use_container_width=True):
                    if edit_name.strip() and edit_pat.strip():
                        db_v2.update_exercise_core(exercise, edit_name.strip(), edit_pat.strip())
                        clean_edit_cache()
                        st.rerun()

        with tab_new:
            new_name = st.text_input("Nombre (Nuevo):")
            default_new_pat = "1, 2, 3, 4, | \n5, 0, 1---"
            
            with st.expander("🎹 Abrir Teclado Virtual (Constructor)"):
                st.caption("Arma tu patrón, escúchalo, cópialo y pégalo abajo.")
                render_virtual_keyboard(default_new_pat)
                
            new_pat = st.text_area("Código del Patrón:", value=default_new_pat, height=120)
            
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                if st.button("▶️ Preview", use_container_width=True, key="prev_new"):
                    try:
                        prev_uri = generate_preview_midi(new_pat, 120)
                        render_midi_player(prev_uri)
                    except Exception: st.error("Error en patrón")
            with col_n2:
                if st.button("➕ Crear", type="primary", use_container_width=True):
                    if new_name.strip() and new_name.strip() not in db["exercises"]:
                        max_order = max([d["order_index"] for d in db["exercises"].values()]) if db["exercises"] else 0
                        db_v2.create_exercise(new_name.strip(), new_pat.strip(), max_order + 1)
                        clean_edit_cache()
                        st.rerun()

        with tab_del:
            st.warning(f"¿Borrar '{exercise}'?")
            if st.button("Sí, borrar", use_container_width=True):
                db_v2.delete_exercise(exercise)
                clean_edit_cache()
                st.rerun()

        with tab_order:
            st.caption("Cambiar posición:")
            keys = list(db["exercises"].keys())
            for i, k in enumerate(keys):
                c1, c2, c3 = st.columns([6, 1.5, 1.5])
                c1.write(k)
                if c2.button("🔼", key=f"up_{k}", disabled=(i == 0)):
                    k_prev = keys[i-1]
                    db_v2.swap_exercise_order(k, db["exercises"][k]["order_index"], k_prev, db["exercises"][k_prev]["order_index"])
                    st.rerun()
                if c3.button("🔽", key=f"dw_{k}", disabled=(i == len(keys)-1)):
                    k_next = keys[i+1]
                    db_v2.swap_exercise_order(k, db["exercises"][k]["order_index"], k_next, db["exercises"][k_next]["order_index"])
                    st.rerun()

        with tab_import:
            st.caption("Pega el JSON directo de Hooktheory")
            import_name = st.text_input("Nombre (Importado):")
            import_json = st.text_area("Código JSON:", height=120)
            
            if st.button("📥 Convertir y Crear", type="primary", use_container_width=True):
                if import_name.strip() and import_json.strip():
                    try:
                        import json
                        data = json.loads(import_json.strip())
                        raw_notes = data.get("notes", [])
                        
                        if not raw_notes and "modern" in data:
                            try: raw_notes = data["modern"]["payload"]["notes"]
                            except: pass
                            
                        keys_data = data.get("keys", [])
                        if not keys_data and "modern" in data:
                            try: keys_data = data["modern"]["payload"]["keys"]
                            except: pass
                            
                        scale_type = "major"
                        if keys_data and isinstance(keys_data, list) and len(keys_data) > 0:
                            scale_type = keys_data[0].get("scale", "major").lower()

                        scale_intervals = {
                            "major": [0, 2, 4, 5, 7, 9, 11],
                            "minor": [0, 2, 3, 5, 7, 8, 10],
                            "dorian": [0, 2, 3, 5, 7, 9, 10],
                            "phrygian": [0, 1, 3, 5, 7, 8, 10],
                            "lydian": [0, 2, 4, 6, 7, 9, 11],
                            "mixolydian": [0, 2, 4, 5, 7, 9, 10],
                            "locrian": [0, 1, 3, 5, 6, 8, 10]
                        }
                        intervals = scale_intervals.get(scale_type, scale_intervals["major"])
                        
                        semitone_to_app = {
                            0: (1, ""), 1: (2, "b"), 2: (2, ""), 3: (3, "b"), 
                            4: (3, ""), 5: (4, ""), 6: (4, "#"), 7: (5, ""), 
                            8: (6, "b"), 9: (6, ""), 10: (7, "b"), 11: (7, "")
                        }
                            
                        if not raw_notes:
                            st.error("No se encontraron notas musicales en el JSON.")
                        else:
                            # 1. ORDENAR NOTAS POR TIEMPO Y MANEJAR SILENCIOS EXPLÍCITOS / HUECOS / ACORDES
                            raw_notes = sorted(raw_notes, key=lambda x: float(x.get("beat", 1.0)))
                            parsed_notes = []
                            current_time = 0.0
                            
                            for n in raw_notes:
                                # Hooktheory "beat" empieza en 1 (el inicio). Restamos 1 para que empiece en tiempo 0.0
                                start_time = float(n.get("beat", 1.0)) - 1.0
                                dur = float(n.get("duration", 1.0))
                                
                                # Si la nota empieza antes que termine la anterior (Acordes/Polifonía), la ignoramos
                                if start_time < current_time - 0.001:
                                    continue
                                
                                # Detectar HUECOS de tiempo y crear silencios automáticos
                                if start_time > current_time + 0.001:
                                    gap_dur = start_time - current_time
                                    parsed_notes.append({"is_rest": True, "abs_deg": 0, "alt": "", "dur": gap_dur})
                                
                                is_rest = n.get("isRest", False)
                                if is_rest:
                                    parsed_notes.append({"is_rest": True, "abs_deg": 0, "alt": "", "dur": dur})
                                else:
                                    sd_str = str(n.get("sd", "1"))
                                    alt_val = 0
                                    if sd_str.startswith("#"): alt_val = 1; sd_str = sd_str[1:]
                                    elif sd_str.startswith("b"): alt_val = -1; sd_str = sd_str[1:]
                                    elif sd_str.endswith("#"): alt_val = 1; sd_str = sd_str[:-1]
                                    elif sd_str.endswith("b"): alt_val = -1; sd_str = sd_str[:-1]
                                    
                                    try: deg_int = int(sd_str)
                                    except: deg_int = 1
                                    
                                    octave_offset = int(n.get("octave", 0))
                                    extra_octaves = (deg_int - 1) // 7
                                    base_deg_idx = ((deg_int - 1) % 7) 
                                    
                                    semitones = intervals[base_deg_idx] + alt_val
                                    extra_octaves += semitones // 12
                                    normalized_semitones = semitones % 12
                                    
                                    app_deg_int, app_alt = semitone_to_app[normalized_semitones]
                                    abs_deg = app_deg_int + ((octave_offset + extra_octaves) * 7)
                                    parsed_notes.append({"is_rest": False, "abs_deg": abs_deg, "alt": app_alt, "dur": dur})
                                    
                                current_time = start_time + dur
                            
                            # 2. TRANSPOSICIÓN INTELIGENTE (AL PISO MÁS BAJO)
                            active_degrees = [n["abs_deg"] for n in parsed_notes if not n["is_rest"]]
                            if active_degrees:
                                min_deg = min(active_degrees)
                                shift = 0
                                # Empujamos la melodía hacia arriba si su nota más baja es menor a 1 (Negativa)
                                while min_deg + shift < 1: 
                                    shift += 7
                                # Bajamos la melodía si su nota más baja está por encima del 7 (Aprovechar espacio)
                                while min_deg + shift > 7: 
                                    shift -= 7
                            else:
                                shift = 0
                                
                            final_str = ""
                            beat_sum = 0.0
                            
                            for i, n in enumerate(parsed_notes):
                                if n["is_rest"]: 
                                    base = "0"
                                else:
                                    final_deg = n["abs_deg"] + shift
                                    # Plegado de emergencia para notas que aún se salgan de 15
                                    while final_deg > 15: final_deg -= 7
                                    while final_deg < 1: final_deg += 7 
                                        
                                    base = f"{final_deg}{n['alt']}"
                                
                                dur = n["dur"]
                                if dur == 4.0: token = f"{base}---"
                                elif dur == 3.0: token = f"{base}--"
                                elif dur == 2.0: token = f"{base}-"
                                elif dur == 1.0: token = f"{base}"
                                else: token = f"{base}[x{dur:g}]"
                                
                                final_str += token
                                beat_sum += dur
                                is_end_of_bar = False
                                
                                # Lógica para insertar barras (|) de forma precisa, incluso tras notas muy largas
                                if beat_sum >= 3.99:
                                    is_end_of_bar = True
                                    while beat_sum >= 3.99:
                                        beat_sum -= 4.0
                                    if beat_sum < 0.01: beat_sum = 0.0
                                
                                if i < len(parsed_notes) - 1:
                                    final_str += ", "
                                    if is_end_of_bar:
                                        final_str += "| \n"
                                else:
                                    if is_end_of_bar: final_str += " |"
                            
                            if import_name.strip() not in db["exercises"]:
                                max_order = max([d["order_index"] for d in db["exercises"].values()]) if db["exercises"] else 0
                                db_v2.create_exercise(import_name.strip(), final_str, max_order + 1)
                                clean_edit_cache()
                                st.success("¡Importado con éxito!")
                                st.rerun()
                            else:
                                st.error("El nombre ya existe. Por favor, elige otro.")
                                
                    except Exception as e:
                        st.error(f"Error parseando JSON: {e}")

# ==============================
# CSS MAESTRO DE COMPACTACIÓN MÓVIL
# ==============================
st.markdown("""
<style>
    /* Reducir el relleno interno de todos los Pop-overs y Formularios */
    div[data-testid="stPopoverBody"] { padding: 0.5rem 0.1rem 2rem 0.1rem !important; }
    div[data-testid="stForm"] { padding: 0.2rem 0.5rem !important; }
    
    /* Eliminar los saltos de línea y espacios entre elementos verticales */
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -0.6rem !important; }
    
    /* Juntar las columnas horizontales al máximo */
    div[data-testid="stHorizontalBlock"] { gap: 0.2rem !important; }
    
    /* Eliminar los títulos (labels) colapsados que dejan un espacio vacío fantasma */
    label:has(> div.st-visually-hidden) { display: none !important; }
    
    /* Achicar la altura de los botones secundarios (🔽🔼) */
    button[kind="secondary"] { min-height: -1rem !important; padding: 0rem !important; }

    /*.st-emotion-cache-wfksaw { flex-flow: row !important; place-items: center; } */

    @media (max-width: 640px) {
    .st-emotion-cache-hua6f6 { min-width: calc(50% - 1.5rem) !important; }
}
/* Proteger el Data Editor de la compactación extrema */
    div[data-testid="stDataFrame"] { margin-bottom: 1rem !important; margin-top: 0.5rem !important; }
</style>
""", unsafe_allow_html=True)

with col_admin2:
    with st.popover("📁 Playlists", use_container_width=True):
        is_archived = "Archivar" in db["exercises"][exercise]["playlists"]
        
        if st.button("🔄 Desarchivar" if is_archived else "📦 Archivar", use_container_width=True):
            pl_list = db["exercises"][exercise]["playlists"]
            if is_archived: pl_list.remove("Archivar")
            else: pl_list.append("Archivar")
            db_v2.update_exercise_playlists(exercise, pl_list)
            if "widget_selector" in st.session_state: del st.session_state["widget_selector"]
            st.rerun()
            
        with st.form("form_etiquetas", border=False):
            st.markdown("<p style='margin-bottom:15; font-weight:bold;'>🏷️ Etiquetas:</p>", unsafe_allow_html=True)
            current_pl = [p for p in db["exercises"][exercise]["playlists"] if p != "Archivar"]
            selected_pl = []
            
            for pl in user_playlists:
                if st.checkbox(pl, value=(pl in current_pl), key=f"chk_{pl}_{exercise}"): 
                    selected_pl.append(pl)
                    
            if st.form_submit_button("💾 Guardar", use_container_width=True):
                final_pl = selected_pl + (["Archivar"] if is_archived else [])
                db_v2.update_exercise_playlists(exercise, final_pl)
                if current_filter != "Todas" and current_filter not in final_pl:
                    if "widget_selector" in st.session_state: del st.session_state["widget_selector"]
                st.rerun()
                
        new_pl = st.text_input("Nueva:", placeholder="Crear nueva...", label_visibility="collapsed")
        if st.button("➕ Crear y agregar", use_container_width=True) and new_pl:
            clean_new = new_pl.strip()
            db_v2.create_playlist(clean_new)
            pl_list = db["exercises"][exercise]["playlists"]
            if clean_new not in pl_list:
                pl_list.append(clean_new)
                db_v2.update_exercise_playlists(exercise, pl_list)
            st.rerun()

# ==============================
# CONFIGURACIONES SÚPER COMPACTAS
# ==============================
stgs = db["exercises"][exercise]["settings"]

master_notes = ["A2","A#2","B2","C3","C#3","D3","D#3","E3","F3","F#3","G3","G#3",
                "A3","A#3","B3","C4","C#4","D4","D#4","E4","F4","F#4","G4","G#4",
                "A4","A#4","B4","C5","C#5","D5"]

val_low = stgs.get("range_low", "A2")
if val_low not in master_notes: val_low = "A2"
val_high = stgs.get("range_high", "A4")
if val_high not in master_notes: val_high = "A4"

with st.popover("⚙️ Ajustes", use_container_width=True):
    with st.form("form_ajustes", border=True):
        
        # 1. Rangos y Transposición (usando select_slider)
        c1, c2 = st.columns(2)
        with c1:
            w_r_low = st.select_slider(
                "LOW", options=master_notes, value=val_low,
                label_visibility="collapsed"
            )
            btn_dw = st.form_submit_button("⬇️")                    
        with c2:
            w_r_high = st.select_slider(
                "HIGH", options=master_notes, value=val_high,
                label_visibility="collapsed"
            )
            btn_up = st.form_submit_button("⬆️")      
        # 2. Dirección (sin etiqueta "Dir:")
        dir_map = {"ascend_descend": "🔼🔽", "descend_ascend": "🔽🔼",
                   "ascend_only": "🔼", "descend_only": "🔽"}
        inv_dir_map = {v: k for k, v in dir_map.items()}
        val_dir = dir_map.get(stgs.get("direction", "ascend_descend"), "🔼🔽")
        w_dir_label = st.radio(
            "Dir", options=list(dir_map.values()),
            index=list(dir_map.values()).index(val_dir),
            horizontal=True, label_visibility="collapsed"
        )
        w_dir = inv_dir_map[w_dir_label]

        c1, c2, c3 = st.columns([3, 3, 2])     
        with c1:
            # 3. BPM
            w_bpm = st.slider(
                "BPM", 0, 400, stgs.get("bpm", 200), 5,
                help="BPM (Velocidad)", label_visibility="collapsed"
            )
        with c2:
            # 4. Repeticiones
            w_repeats = st.slider(
                "Repeticiones", 1, 100, stgs.get("repeats", 1), 1,
                help="Repeticiones por nota", label_visibility="collapsed"
            )
        with c3:
            btn_sv = st.form_submit_button("💾", type="primary", use_container_width=True)

        if btn_up or btn_dw or btn_sv:
            new_stgs = dict(stgs)
            new_stgs["direction"] = w_dir
            new_stgs["bpm"] = w_bpm
            new_stgs["repeats"] = w_repeats # <--- GUARDAR REPETICIONES

            if btn_up or btn_dw:
                idx_low = master_notes.index(w_r_low)
                idx_high = master_notes.index(w_r_high)
                shift = 1 if btn_up else -1
                new_stgs["range_low"] = master_notes[max(0, min(len(master_notes)-1, idx_low + shift))]
                new_stgs["range_high"] = master_notes[max(0, min(len(master_notes)-1, idx_high + shift))]
            else:
                new_stgs["range_low"] = w_r_low
                new_stgs["range_high"] = w_r_high

            db_v2.update_exercise_settings(exercise, new_stgs)
            st.rerun()

with st.popover("🎛️ Volumenes", use_container_width=True):
    with st.form("form_mezcladora", border=True):
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<small style='color:gray;'>🥁 Metrónomo</small>", unsafe_allow_html=True)
            w_m_vol = st.slider(
                "Metrónomo", 0, 127, stgs.get("metronome_vol", 80), 10,
                label_visibility="collapsed"
            )
            st.markdown("<small style='color:gray;'>🌉 Puente</small>", unsafe_allow_html=True)
            w_bridge = st.slider(
                "Puente", 0, 32, stgs.get("bridge", 4), 1,
                label_visibility="collapsed"
            )
        with col2:
            st.markdown("<small style='color:gray;'>🎵 Notas</small>", unsafe_allow_html=True)
            w_n_vol = st.slider(
                "Notas Vol.", 0, 127, stgs.get("notes_vol", 127), 10,
                label_visibility="collapsed"
            )
            st.markdown("<small style='color:gray;'>🎹 Acorde fin</small>", unsafe_allow_html=True)
            w_f_vol = st.slider(
                "Chord Vol.", 0, 127, stgs.get("final_chord_vol", 85), 10,
                label_visibility="collapsed"
            )

        if st.form_submit_button("💾 Guardar Mezcla", type="primary", use_container_width=True):
            new_stgs = dict(stgs)
            new_stgs["bridge"] = w_bridge
            new_stgs["metronome_vol"] = w_m_vol
            new_stgs["notes_vol"] = w_n_vol
            new_stgs["final_chord_vol"] = w_f_vol
            db_v2.update_exercise_settings(exercise, new_stgs)
            st.rerun()

# ==============================
# BOTÓN PARA GENERAR MIDI
# ==============================
if st.button("Generar MIDI", type="primary", use_container_width=True):
    with st.spinner("Creando audio..."):
        try:
            file_name, midi_uri, peaks_data = generate_midi(exercise, db["exercises"][exercise]["pattern"], stgs)
            st.success(f"✅ {file_name}")
            render_midi_player(midi_uri, peaks_data)
        except Exception as e:
            st.error(f"❌ Error de sintaxis en el patrón: {e}")
