# --- START OF FILE app_v2.py ---
import streamlit as st
import database_v2 as db_v2
from music_engine import generate_midi
from ui_components import render_midi_player

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

with st.popover(f"📂 Carpeta: {st.session_state.widget_filter}", use_container_width=True):
    st.radio("Selecciona carpeta:", all_filters, key="widget_filter", on_change=update_filter, label_visibility="collapsed")

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
# MENÚS ADMINISTRACIÓN
# ==============================
col_admin1, col_admin2 = st.columns(2)

with col_admin1:
    with st.popover("🛠️ Modificar BD", use_container_width=True):
        tab_edit, tab_new, tab_del, tab_order = st.tabs(["✏️ Editar", "➕ Crear", "🗑️ Borrar", "🔄 Ordenar"])

        with tab_edit:
            edit_name = st.text_input("Nombre:", value=exercise)
            edit_pat = st.text_area("Patrón musical:", value=db["exercises"][exercise]["pattern"], height=100)
            if st.button("Guardar cambios", type="primary", use_container_width=True):
                if edit_name.strip() and edit_pat.strip():
                    db_v2.update_exercise_core(exercise, edit_name.strip(), edit_pat.strip())
                    clean_edit_cache()
                    st.rerun()

        with tab_new:
            new_name = st.text_input("Nombre:")
            new_pat = st.text_area("Patrón:", height=100)
            if st.button("Crear", type="primary", use_container_width=True):
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

with col_admin2:
    with st.popover("📁 Playlists & Archivo", use_container_width=True):
        is_archived = "Archivar" in db["exercises"][exercise]["playlists"]
        
        if st.button("🔄 Desarchivar" if is_archived else "📦 Archivar", use_container_width=True):
            pl_list = db["exercises"][exercise]["playlists"]
            if is_archived: pl_list.remove("Archivar")
            else: pl_list.append("Archivar")
            db_v2.update_exercise_playlists(exercise, pl_list)
            
            # Limpiar memoria visual si desaparece de la vista actual
            if "widget_selector" in st.session_state:
                del st.session_state["widget_selector"]
            st.rerun()
            
        st.divider()
        with st.form("form_etiquetas", border=False):
            st.write("🏷️ **Etiquetas:**")
            current_pl = [p for p in db["exercises"][exercise]["playlists"] if p != "Archivar"]
            selected_pl = []
            
            for pl in user_playlists:
                # SOLUCIÓN ERROR 2: Incluir el nombre del ejercicio en el 'key' del checkbox.
                # Esto obliga a la interfaz a cargar los datos reales, y no los "reciclados".
                dynamic_key = f"chk_{pl}_{exercise}"
                if st.checkbox(pl, value=(pl in current_pl), key=dynamic_key): 
                    selected_pl.append(pl)
                    
            if st.form_submit_button("💾 Guardar etiquetas", use_container_width=True):
                final_pl = selected_pl + (["Archivar"] if is_archived else [])
                db_v2.update_exercise_playlists(exercise, final_pl)
                
                # Si se eliminó de la lista actual, borrar la selección de la memoria
                if current_filter != "Todas" and current_filter not in final_pl:
                    if "widget_selector" in st.session_state:
                        del st.session_state["widget_selector"]
                        
                st.rerun()
                
        st.divider()
        new_pl = st.text_input("Crear nueva categoría:")
        if st.button("Crear y agregar", use_container_width=True) and new_pl:
            clean_new = new_pl.strip()
            db_v2.create_playlist(clean_new)
            
            pl_list = db["exercises"][exercise]["playlists"]
            if clean_new not in pl_list:
                pl_list.append(clean_new)
                db_v2.update_exercise_playlists(exercise, pl_list)
            st.rerun()

# ==============================
# CONFIGURACIONES
# ==============================
stgs = db["exercises"][exercise]["settings"]

# Lista maestra ordenada cromáticamente (esencial para hacer cálculos de semitonos)
master_notes = ["A2","A#2","B2","C3","C#3","D3","D#3","E3","F3","F#3","G3","G#3",
                "A3","A#3","B3","C4","C#4","D4","D#4","E4","F4","F#4","G4","G#4",
                "A4","A#4","B4","C5","C#5","D5"]

# Aseguramos que los valores existan en la lista (fallback de seguridad)
val_low = stgs.get("range_low", "A2")
if val_low not in master_notes: val_low = "A2"
val_high = stgs.get("range_high", "A4")
if val_high not in master_notes: val_high = "A4"

with st.popover("⚙️ Ajustes (Rango, Dirección, BPM)", use_container_width=True):
    # FORMULARIO 1: Evita el guardado automático al mover los sliders
    with st.form("form_ajustes", border=False):
        opts_dir = ["ascend_descend","descend_ascend","ascend_only","descend_only"]

        w_r_low = st.select_slider("Rango LOW", options=master_notes, value=val_low)
        w_r_high = st.select_slider("Rango HIGH", options=master_notes, value=val_high)
        w_dir = st.select_slider("Dirección", options=opts_dir, value=stgs.get("direction", "ascend_descend"))
        w_bpm = st.slider("BPM", 0, 400, stgs.get("bpm", 200), 5)

        st.write("🔄 **Transponer rango completo:**")
        c1, c2 = st.columns(2)
        btn_dw = c1.form_submit_button("🔽 Bajar -1", use_container_width=True)
        btn_up = c2.form_submit_button("🔼 Subir +1", use_container_width=True)
        
        # Botón Guardar principal
        btn_sv = st.form_submit_button("💾 Guardar Ajustes", type="primary", use_container_width=True)

        if btn_up or btn_dw or btn_sv:
            new_stgs = dict(stgs)
            new_stgs["direction"] = w_dir
            new_stgs["bpm"] = w_bpm

            if btn_up or btn_dw:
                # 1. Obtenemos el índice actual en la lista maestra
                idx_low = master_notes.index(w_r_low)
                idx_high = master_notes.index(w_r_high)
                
                # 2. Aplicamos +1 o -1
                shift = 1 if btn_up else -1
                
                # 3. Calculamos nuevo índice, limitando con max(0) y min(límite superior) de forma independiente
                new_idx_low = max(0, min(len(master_notes)-1, idx_low + shift))
                new_idx_high = max(0, min(len(master_notes)-1, idx_high + shift))
                
                new_stgs["range_low"] = master_notes[new_idx_low]
                new_stgs["range_high"] = master_notes[new_idx_high]
            else:
                # Si solo presionó Guardar Ajustes
                new_stgs["range_low"] = w_r_low
                new_stgs["range_high"] = w_r_high

            db_v2.update_exercise_settings(exercise, new_stgs)
            st.rerun()

with st.popover("🎛️ Mezcladora", use_container_width=True):
    # FORMULARIO 2: Evita el lag en la mezcladora
    with st.form("form_mezcladora", border=False):
        w_bridge = st.slider("Puente", 0, 32, stgs.get("bridge", 4), 1)
        w_m_vol = st.slider("Metrónomo", 0, 127, stgs.get("metronome_vol", 80), 10)
        w_n_vol = st.slider("Notas Vol.", 0, 127, stgs.get("notes_vol", 127), 10)
        w_f_vol = st.slider("Chord Vol.", 0, 127, stgs.get("final_chord_vol", 85), 10)

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
            file_name, midi_uri = generate_midi(exercise, db["exercises"][exercise]["pattern"], stgs)
            st.success(f"✅ {file_name}")
            render_midi_player(midi_uri)
        except Exception as e:
            st.error(f"❌ Error de sintaxis en el patrón: {e}")
