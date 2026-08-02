# --- START OF FILE app_v2.py ---
import streamlit as st
import database_v2 as db_v2
from music_engine import generate_midi
from ui_components import render_midi_player

db = db_v2.load_db()

def clean_edit_cache():
    for key in ["in_ed_name", "in_ed_pat", "widget_selector"]:
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
if current_filter == "Todas": available_exs = [name for name, d in db["exercises"].items() if "Archivar" not in d["playlists"]]
elif current_filter == "📦 Archivados": available_exs = [name for name, d in db["exercises"].items() if "Archivar" in d["playlists"]]
else: available_exs = [name for name, d in db["exercises"].items() if current_filter in d["playlists"] and "Archivar" not in d["playlists"]]

if not available_exs:
    st.info(f"No hay ejercicios en la categoría '{current_filter}'.")
    st.stop()

if "widget_selector" not in st.session_state or st.session_state.widget_selector not in available_exs:
    last_ex = db.get("last_selected_exercise")
    st.session_state.widget_selector = last_ex if last_ex in available_exs else available_exs[0]
    db_v2.update_pref_exercise(st.session_state.widget_selector)

def sync_selection():
    db_v2.update_pref_exercise(st.session_state.widget_selector)
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
            st.rerun()
            
        st.divider()
        with st.form("form_etiquetas", border=False):
            st.write("🏷️ **Etiquetas:**")
            current_pl = [p for p in db["exercises"][exercise]["playlists"] if p != "Archivar"]
            selected_pl = []
            for pl in user_playlists:
                if st.checkbox(pl, value=(pl in current_pl)): selected_pl.append(pl)
                    
            if st.form_submit_button("💾 Guardar etiquetas", use_container_width=True):
                final_pl = selected_pl + (["Archivar"] if is_archived else [])
                db_v2.update_exercise_playlists(exercise, final_pl)
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

def save_settings():
    new_stgs = {
        "range_low": st.session_state.w_r_low, "range_high": st.session_state.w_r_high,
        "direction": st.session_state.w_dir, "bpm": st.session_state.w_bpm,
        "bridge": st.session_state.w_bridge, "metronome_vol": st.session_state.w_m_vol,
        "notes_vol": st.session_state.w_n_vol, "final_chord_vol": st.session_state.w_f_vol
    }
    db_v2.update_exercise_settings(exercise, new_stgs)

with st.popover("⚙️ Ajustes (Rango, Dirección, BPM)", use_container_width=True):
    opts_low = ["A2","A#2","B2","C3","C#3","D3","D#3","E3","F3","F#3","G3","G#3","A3","A#3","B3","C4","C#4","D4","D#4","E4","F4","F#4","G4","G#4","A4"]
    opts_high = ["A4","G#4","G4","F#4","F4","E4","D#4","D4","C#4","C4","B3","A#3","A3","G#3","G3","F#3","F3","E3","D#3","D3","C#3","C3","B2","A#2","A2","D5","C#5","C5","B4","A#4"]
    opts_dir = ["ascend_descend","descend_ascend","ascend_only","descend_only"]

    st.select_slider("Rango LOW", options=opts_low, value=stgs.get("range_low", "A2"), key="w_r_low", on_change=save_settings)
    st.select_slider("Rango HIGH", options=opts_high, value=stgs.get("range_high", "C5"), key="w_r_high", on_change=save_settings)
    st.select_slider("Dirección", options=opts_dir, value=stgs.get("direction", "ascend_descend"), key="w_dir", on_change=save_settings)
    st.slider("BPM", 0, 400, stgs.get("bpm", 200), 5, key="w_bpm", on_change=save_settings)

with st.popover("🎛️ Mezcladora", use_container_width=True):
    st.slider("Puente", 0, 32, stgs.get("bridge", 4), 1, key="w_bridge", on_change=save_settings)
    st.slider("Metrónomo", 0, 127, stgs.get("metronome_vol", 80), 10, key="w_m_vol", on_change=save_settings)
    st.slider("Notas Vol.", 0, 127, stgs.get("notes_vol", 127), 10, key="w_n_vol", on_change=save_settings)
    st.slider("Chord Vol.", 0, 127, stgs.get("final_chord_vol", 85), 10, key="w_f_vol", on_change=save_settings)

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