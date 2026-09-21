import math
import base64
from midiutil import MIDIFile

NOTE_NAMES = {"C":0,"C#":1,"D":2,"D#":3,"E":4,"F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11}

def note_to_midi(note):
    return 12 * (int(note[-1]) + 1) + NOTE_NAMES[note[:-1]]

def parse_pattern(pat):
    result = []
    # Limpiamos espacios, saltos de línea y barras divisorias decorativas
    clean_pat = pat.replace(" ", "").replace("|", "").replace("\n", "")
    
    for token in clean_pat.split(","):
        if not token: continue 
        
        # 1. Extraer duración fraccionaria si usa [x0.5]
        if "[x" in token:
            degree, length_str = token.split("[x")
            length = float(length_str[:-1])
            token = degree
        else:
            length = 1.0
            
        # 2. Extraer duración por guiones (Ej: 1--- = 4 tiempos)
        dashes = token.count("-")
        if dashes > 0:
            length = 1.0 + dashes
            token = token.replace("-", "") # Quitamos los guiones para quedarnos con el número
            
        # 3. Detectar nota, alteración o silencio (Ahora acepta el 0)
        if token.upper() == "R" or token == "0": 
            result.append((0, length, 0)) # El 0 absoluto es silencio
        elif token.endswith("b"): 
            result.append((int(token[:-1]), length, -1))
        elif token.endswith("#"): 
            result.append((int(token[:-1]), length, +1))
        else: 
            result.append((int(token), length, 0))
            
    return result

def build_major_scale(root_midi):
    return [root_midi + i for i in [0,2,4,5,7,9,11,12,14,16,17,19,21,23,24]]

def pattern_fits_in_range(pattern_degrees, root, high_midi):
    scale = build_major_scale(root)
    # NUEVO: Ignoramos los silencios (degree 0) para calcular la nota más alta
    active_degrees = [deg for deg,_,_ in pattern_degrees if deg > 0]
    if not active_degrees: return True
    max_degree = max(active_degrees)
    return scale[max_degree-1] <= high_midi

def generate_midi(exercise_name, pattern_str, settings):
    pattern_notes = parse_pattern(pattern_str)
    bpm = settings["bpm"]
    repeats = settings.get("repeats", 1)
    range_low, range_high = settings["range_low"], settings["range_high"]
    direction = settings["direction"]
    bridge = settings["bridge"]
    metronome_vol = settings["metronome_vol"]
    notes_vol = settings["notes_vol"]
    final_chord_vol = settings["final_chord_vol"]

    mf = MIDIFile(2) 
    mf.addTempo(0, 0, bpm)
    mf.addTempo(1, 0, bpm)
    channel_drums, woodblock = 9, 76

    low_midi, high_midi = note_to_midi(range_low), note_to_midi(range_high)
    roots_up, root = [], low_midi
    while root <= high_midi:
        if not pattern_fits_in_range(pattern_notes, root, high_midi): break
        roots_up.append(root); root += 1

    dir_lower = direction.lower().replace(" ", "_")
    if dir_lower in ("ascend_only","low_to_high"): roots = roots_up
    elif dir_lower in ("descend_only","high_to_low"):
        start_root = high_midi
        while start_root >= low_midi and not pattern_fits_in_range(pattern_notes, start_root, high_midi): start_root -= 1
        roots = list(range(start_root, low_midi-1, -1))
    elif dir_lower in ("ascend_descend","up_down"): roots = roots_up + roots_up[-2::-1]
    elif dir_lower in ("descend_ascend","down_up"):
        roots_down = [r for r in range(high_midi, low_midi-1, -1) if pattern_fits_in_range(pattern_notes, r, high_midi)]
        roots = roots_down + roots_down[-2::-1]
    else: roots = roots_up

    # ==========================
    # 1. GENERAR PISTA MELÓDICA
    # ==========================
    time = 4.0 # Dejamos 4 tiempos al inicio (Count-in)
    peaks_data = [] # NUEVO: Guardará la nota pico de cada bloque
    
    for i, root in enumerate(roots):
        scale = build_major_scale(root)
        
        for rep in range(repeats):
            rep_start_beat = time
            rep_max_pitch = -1
            
            # 1. Tocar las notas del patrón
            for idx, (degree, length, accidental) in enumerate(pattern_notes, start=1):
                
                # NUEVO: Si es un silencio (0), solo avanzamos el tiempo y continuamos
                if degree == 0:
                    time += length
                    continue
                    
                note_num = scale[degree-1] + accidental
                if note_num > rep_max_pitch:
                    rep_max_pitch = note_num
                mf.addNote(0, 0, note_num, time, length, notes_vol)
                time += length

            rep_end_beat = time
            
            # Guardamos la nota más alta de esta repetición y sus tiempos en segundos
            peaks_data.append({
                "start": rep_start_beat * (60.0 / bpm),
                "end": rep_end_beat * (60.0 / bpm),
                "pitch": rep_max_pitch
            })

            # 2. Lógica del Puente (Bridge)
            if rep < repeats - 1:
                mf.addNote(0, 0, root, time, bridge, notes_vol)
                time += bridge
            elif i < len(roots) - 1:
                next_root = roots[i+1]
                mf.addNote(0, 0, next_root, time, bridge, notes_vol)
                time += bridge

    # Acorde final
    final_scale = build_major_scale(low_midi)
    final_chord_start = time
    final_max_pitch = -1
    for degree,_,_ in pattern_notes:
        if degree == 0: continue # NUEVO: Omitir silencios en el acorde final
        
        note_num = final_scale[degree-1]
        if note_num > final_max_pitch:
            final_max_pitch = note_num
        mf.addNote(0, 0, note_num, time, 4, final_chord_vol)
    time += 4.0 
    
    peaks_data.append({
        "start": final_chord_start * (60.0 / bpm),
        "end": time * (60.0 / bpm),
        "pitch": final_max_pitch
    })

    # ==========================
    # 2. GENERAR METRÓNOMO INDEPENDIENTE
    # ==========================
    total_beats = int(math.ceil(time))
    beats_per_measure = 4  # Asumimos un compás estándar de 4/4
    
    # 76 = High Wood Block (Agudo), 77 = Low Wood Block (Grave)
    # (Opcional: Si prefieres el sonido clásico mecánico, cambia a 34 y 33)
    sound_accent = 76  
    sound_normal = 77  

    for b in range(total_beats):
        if b % beats_per_measure == 0:
            # Tiempo 1 (Inicio de compás): Sonido agudo y un poco más fuerte
            accent_vol = min(127, metronome_vol + 15) if metronome_vol > 0 else 0
            mf.addNote(1, channel_drums, sound_accent, float(b), 0.5, accent_vol)
        else:
            # Tiempos 2, 3 y 4: Sonido grave y volumen normal
            mf.addNote(1, channel_drums, sound_normal, float(b), 0.5, metronome_vol)

    # === GUARDAR Y RETORNAR (Esto es lo que seguramente faltaba) ===
    file_name = f"{exercise_name}_{bpm}bpm_{range_low}-{range_high}_{direction}.mid"
    with open(file_name, "wb") as f: 
        mf.writeFile(f)
    
    with open(file_name, "rb") as f: 
        midi_data = f.read()
        
    b64_midi = base64.b64encode(midi_data).decode("utf-8")
    midi_uri = f"data:audio/midi;base64,{b64_midi}"
    
    return file_name, midi_uri, peaks_data

# Añadir al final de music_engine.py
def generate_preview_midi(pattern_str, bpm=120):
    """Genera un archivo MIDI corto de 1 sola repetición para previsualizar"""
    pattern_notes = parse_pattern(pattern_str)
    
    # Creamos un archivo de 1 sola pista para el preview (sin metrónomo)
    mf = MIDIFile(1)
    mf.addTempo(0, 0, bpm)
    
    time = 0.0
    # Usamos C4 (Midi 60) como nota base para el preview
    scale = build_major_scale(60) 
    
    for idx, (degree, length, accidental) in enumerate(pattern_notes):
        if degree == 0:  # Lógica de silencios
            time += length
            continue
            
        note_num = scale[degree-1] + accidental
        mf.addNote(0, 0, note_num, time, length, 100)
        time += length
        
    file_name = "preview_temp.mid"
    with open(file_name, "wb") as f: 
        mf.writeFile(f)
        
    with open(file_name, "rb") as f: 
        midi_data = f.read()
        
    b64_midi = base64.b64encode(midi_data).decode("utf-8")
    return f"data:audio/midi;base64,{b64_midi}"
