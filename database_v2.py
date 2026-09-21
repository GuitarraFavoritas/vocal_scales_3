import os
import streamlit as st
from supabase import create_client, Client

DEFAULT_SETTINGS = {
    "range_low": "A2", "range_high": "A4", "direction": "ascend_descend",
    "bpm": 200, "bridge": 4, "metronome_vol": 80, "notes_vol": 127, "final_chord_vol": 80,
    "repeats": 1
}

@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase_client = init_connection()

@st.cache_resource
def load_db():
    """Descarga los datos relacionales y los empaqueta en un diccionario para la UI."""
    data = {"playlists": [], "exercises": {}}
    
    # 1. Cargar Preferencias
    prefs_res = supabase_client.table("v2_prefs").select("*").eq("id", 1).execute()
    if prefs_res.data:
        data["last_selected_filter"] = prefs_res.data[0]["last_filter"]
        data["last_selected_exercise"] = prefs_res.data[0]["last_exercise"]
        
    # 2. Cargar Playlists
    pl_res = supabase_client.table("v2_playlists").select("name").execute()
    data["playlists"] = [row["name"] for row in pl_res.data]
    
    # 3. Cargar Ejercicios ordenados
    ex_res = supabase_client.table("v2_exercises").select("*").order("order_index").execute()
    for row in ex_res.data:
        data["exercises"][row["name"]] = {
            "pattern": row["pattern"],
            "order_index": row["order_index"],
            "playlists": row["playlists"] if row["playlists"] else [],
            "settings": {k: row.get(k, DEFAULT_SETTINGS[k]) for k in DEFAULT_SETTINGS.keys()}
        }
        
    return data

# ==========================================
# FUNCIONES OPTIMIZADAS (ACTUALIZACIÓN EN MEMORIA)
# ==========================================

def update_pref_filter(filter_name):
    supabase_client.table("v2_prefs").update({"last_filter": filter_name}).eq("id", 1).execute()
    load_db()["last_selected_filter"] = filter_name # Modifica el caché local al instante

def update_pref_exercise(ex_name):
    supabase_client.table("v2_prefs").update({"last_exercise": ex_name}).eq("id", 1).execute()
    load_db()["last_selected_exercise"] = ex_name

def update_exercise_settings(ex_name, settings):
    supabase_client.table("v2_exercises").update(settings).eq("name", ex_name).execute()
    load_db()["exercises"][ex_name]["settings"] = settings

def update_exercise_playlists(ex_name, playlists):
    supabase_client.table("v2_exercises").update({"playlists": playlists}).eq("name", ex_name).execute()
    load_db()["exercises"][ex_name]["playlists"] = playlists

def create_playlist(pl_name):
    try:
        supabase_client.table("v2_playlists").insert({"name": pl_name}).execute()
        if pl_name not in load_db()["playlists"]:
            load_db()["playlists"].append(pl_name)
    except Exception: pass

def update_exercise_core(old_name, new_name, new_pattern):
    supabase_client.table("v2_exercises").update({"name": new_name, "pattern": new_pattern}).eq("name", old_name).execute()
    db = load_db()
    # Mover los datos al nuevo nombre en el caché local
    db["exercises"][new_name] = db["exercises"].pop(old_name)
    db["exercises"][new_name]["pattern"] = new_pattern

def create_exercise(name, pattern, order_index):
    try:
        supabase_client.table("v2_exercises").insert({
            "name": name, "pattern": pattern, "order_index": order_index
        }).execute()
        load_db()["exercises"][name] = {
            "pattern": pattern,
            "order_index": order_index,
            "playlists": [],
            "settings": DEFAULT_SETTINGS.copy()
        }
    except Exception as e:
        st.error(f"Error al crear: {e}")

def delete_exercise(name):
    supabase_client.table("v2_exercises").delete().eq("name", name).execute()
    load_db()["exercises"].pop(name, None)

def swap_exercise_order(name1, order1, name2, order2):
    supabase_client.table("v2_exercises").update({"order_index": order2}).eq("name", name1).execute()
    supabase_client.table("v2_exercises").update({"order_index": order1}).eq("name", name2).execute()
    
    # Actualizar órdenes locales
    db = load_db()
    db["exercises"][name1]["order_index"] = order2
    db["exercises"][name2]["order_index"] = order1
    
    # Reordenar el diccionario local para que la UI lo refleje de inmediato
    db["exercises"] = dict(sorted(db["exercises"].items(), key=lambda item: item[1]["order_index"]))
