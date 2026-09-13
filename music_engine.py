import math
import base64
from midiutil import MIDIFile

NOTE_NAMES = {"C":0,"C#":1,"D":2,"D#":3,"E":4,"F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11}

def note_to_midi(note):
    return 12 * (int(note[-1]) + 1) + NOTE_NAMES[note[:-1]]

def parse_pattern(pat):
    result = []
    for token in pat.replace(" ", "").split(","):
        if "[x" in token:
            degree, length = token.split("[x")
            length = float(length[:-1])
        else:
            degree, length = token, 1.0
        if degree.endswith("b"): result.append((int(degree[:-1]), length, -1))
        elif degree.endswith("#"): result.append((int(degree[:-1]), length, +1))
        else: result.append((int(degree), length, 0))
    return result

def build_major_scale(root_midi):
    return [root_midi + i for i in [0,2,4,5,7,9,11,12,14,16,17,19,21,23,24]]

def pattern_fits_in_range(pattern_degrees, root, high_midi):
    scale = build_major_scale(root)
    max_degree = max(deg for deg,_,_ in pattern_degrees)
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
    for b in range(total_beats):
        mf.addNote(1, channel_drums, woodblock, float(b), 0.5, metronome_vol)

    file_name = f"{exercise_name}_{bpm}bpm_{range_low}-{range_high}_{direction}.mid"
    with open(file_name, "wb") as f: 
        mf.writeFile(f)
    
    with open(file_name, "rb") as f: 
        midi_data = f.read()
        
    b64_midi = base64.b64encode(midi_data).decode("utf-8")
    midi_uri = f"data:audio/midi;base64,{b64_midi}"
    
    # NUEVO: Devolvemos también la lista de picos (peaks_data)
    return file_name, midi_uri, peaks_data
