import os
import json
import streamlit.components.v1 as components

# ==============================================================
# 1. COMPONENTE: REPRODUCTOR MIDI
# ==============================================================
def render_midi_player(midi_uri, peaks_data=None):
    if peaks_data is None: peaks_data = []
    peaks_json = json.dumps(peaks_data)
    
    html_player = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="https://cdn.jsdelivr.net/combine/npm/tone@14.7.58,npm/@magenta/music@1.23.1/es6/core.js,npm/focus-visible@5,npm/html-midi-player@1.5.0"></script>
    <style>
        * {{ box-sizing: border-box; }} 
        body {{ margin: 0; padding: 0; width: 100vw; background-color: #121212; overflow-x: hidden; font-family: sans-serif; }} 
        midi-player {{ width: 100%; display: block; margin: 10px 0; }}
        
        #display-container {{ display: flex; justify-content: center; gap: 15px; margin: 10px 0 5px 0; }}
        
        .note-box-container {{ display: flex; flex-direction: column; align-items: center; width: 140px; }}
        .note-box-label {{ color: #888; font-size: 0.8rem; margin-bottom: 5px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
        
        .note-box {{
            font-size: 2.2rem; font-weight: 900; color: #444; 
            background: #1a1a1a; padding: 10px 0; width: 100%;
            border-radius: 12px; border: 2px solid #333;
            text-align: center; transition: all 0.05s ease-out;
        }}
        
        #note-display.active {{
            color: #FFD700; border-color: #FFD700;
            text-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
            transform: scale(1.05);
        }}
        
        #peak-display.active {{
            color: #00BFFF; border-color: #00BFFF;
            text-shadow: 0 0 15px rgba(0, 191, 255, 0.6);
        }}
    </style>
    </head><body>
    <div style="display: flex; flex-direction: column; width: 100%; gap: 5px; padding: 5px;">
        <div id="display-container">
            <div class="note-box-container">
                <div class="note-box-label">Nota Actual</div>
                <div id="note-display" class="note-box">--</div>
            </div>
            <div class="note-box-container">
                <div class="note-box-label">Top Repetición</div>
                <div id="peak-display" class="note-box">--</div>
            </div>
        </div>
        <midi-player src="{midi_uri}" sound-font></midi-player>
    </div>
    <script>
        const peaksData = {peaks_json};
        const notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        function getNoteName(pitch) {{
            const octave = Math.floor(pitch / 12) - 1;
            return notes[pitch % 12] + octave;
        }}
        
        const noteDisplay = document.getElementById('note-display');
        const peakDisplay = document.getElementById('peak-display');
        const player = document.querySelector('midi-player');
        
        let animationId;
        let currentActiveNote = null;

        function checkPlaybackTime() {{
            if (player.playing && player.noteSequence) {{
                const time = player.currentTime;
                
                const activeNotes = player.noteSequence.notes.filter(n => time >= n.startTime && time < n.endTime && !n.isDrum);
                if (activeNotes.length > 0) {{
                    const note = activeNotes[0];
                    if (currentActiveNote !== note) {{
                        currentActiveNote = note;
                        noteDisplay.innerText = getNoteName(note.pitch);
                        noteDisplay.classList.remove('active');
                        void noteDisplay.offsetWidth; 
                    }}
                    if (time < note.endTime - 0.02) {{ noteDisplay.classList.add('active'); }} 
                    else {{ noteDisplay.classList.remove('active'); }}
                }} else {{
                    if (currentActiveNote !== null) {{
                        currentActiveNote = null;
                        noteDisplay.innerText = "--";
                        noteDisplay.classList.remove('active');
                    }}
                }}
                
                const currentPeak = peaksData.find(p => time < p.end);
                if (currentPeak) {{
                    const peakNoteName = getNoteName(currentPeak.pitch);
                    if (peakDisplay.innerText !== peakNoteName) {{
                        peakDisplay.innerText = peakNoteName;
                        peakDisplay.classList.add('active');
                    }}
                }} else {{
                    peakDisplay.innerText = "--";
                    peakDisplay.classList.remove('active');
                }}
            }}
            animationId = requestAnimationFrame(checkPlaybackTime);
        }}
        
        player.addEventListener('start', () => {{ 
            currentActiveNote = null; 
            animationId = requestAnimationFrame(checkPlaybackTime); 
        }});
        
        player.addEventListener('stop', () => {{ 
            cancelAnimationFrame(animationId); 
            currentActiveNote = null; 
            noteDisplay.innerText = "--"; 
            noteDisplay.classList.remove('active'); 
            peakDisplay.innerText = "--";
            peakDisplay.classList.remove('active'); 
        }});
    </script>
    </body></html>
    """
    components.html(html_player, height=190)


# ==============================================================
# 2. COMPONENTE BIDIRECCIONAL: TECLADO VIRTUAL CON METRÓNOMO
# ==============================================================
_KBD_DIR = os.path.join(os.path.dirname(__file__), "kbd_component")
os.makedirs(_KBD_DIR, exist_ok=True)

html_code = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/combine/npm/tone@14.7.58"></script>
<style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 2px; font-family: sans-serif; background: #121212; color: white; display: flex; flex-direction: column; align-items: center; overflow: hidden; }
    
    .screen { background: #000; border: 2px solid #444; border-radius: 6px; width: 100%; padding: 15px; min-height: 220px; max-height: 220px; overflow-y: auto; font-family: monospace; font-size: 0.9rem; color: #00ff00; margin-bottom: 8px; white-space: normal; line-height: 2.8; }
    .screen::-webkit-scrollbar { width: 5px; }
    .screen::-webkit-scrollbar-thumb { background-color: #555; border-radius: 3px; }
    
    .dur-05 { display: inline-block; border-bottom: 2px solid #00ff00; padding-bottom: 2px; }
    .dur-025 { display: inline-block; border-bottom: 4px double #00ff00; padding-bottom: 2px; }
    .dur-0125 { display: inline-block; position: relative; border-bottom: 1px solid #00ff00; padding-bottom: 2px; }
    .dur-0125::after { content: ''; position: absolute; left: 0; right: 0; bottom: -5px; height: 1px; border-top: 1px solid #00ff00; border-bottom: 1px solid #00ff00; }
    .bar-line { color: #777; margin: 0 4px; font-weight: bold; font-size: 0.9rem; }
    
    .controls-wrapper { width: 100%; padding: 0 5px; }
    
    /* Panel del Metrónomo */
    .metro-container { display: flex; align-items: center; justify-content: space-between; background: #222; border: 1px solid #444; padding: 6px 10px; border-radius: 4px; margin-bottom: 8px; font-size: 0.8rem; }
    .metro-toggle { cursor: pointer; display: flex; align-items: center; gap: 5px; font-weight: bold; user-select: none; }
    #bpm-slider { flex: 1; margin-left: 15px; cursor: pointer; accent-color: #00BFFF; }
    #bpm-val { color: #00BFFF; width: 30px; display: inline-block; text-align: right; }
    
    /* Controles de Duración y Teclado */
    .dur-controls { display: grid; grid-template-columns: repeat(6, 1fr); gap: 4px; margin-bottom: 8px; }
    .dur-btn { background: #222; border: 1px solid #555; color: white; padding: 5px 0; border-radius: 4px; cursor: pointer; text-align: center; font-size: 0.7rem; transition: 0.1s; user-select: none; }
    .dur-btn.active { background: #00BFFF; color: black; font-weight: bold; border-color: #008CBA; transform: scale(1.05); }
    
    .keyboard-row { display: grid; grid-template-columns: repeat(10, 1fr); gap: 4px; margin-bottom: 8px; }
    .key { background: #333; border: 1px solid #555; border-radius: 4px; padding: 6px 0; font-size: 0.8rem; font-weight: bold; color: white; cursor: pointer; text-align: center; transition: 0.1s; user-select: none; }
    .key:active { background: #FFD700; color: black; transform: scale(0.95); }
    .key.rest { background: #1a4b6e; border-color: #2a7baf; }
    .key.octave { background: #4a1a6e; border-color: #7a2aaf; }
    
    .controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-bottom: 5px; }
    .btn { padding: 8px; font-size: 1rem; border-radius: 4px; border: none; cursor: pointer; color: white; }
    .btn-play { background: #28a745; }
    .btn-undo { background: #fd7e14; }
    .btn-clear { background: #dc3545; }
</style>
</head><body>

<div class="screen" id="display">...</div>

<div class="controls-wrapper">
    <!-- NUEVO: Panel de Metrónomo y Velocidad -->
    <div class="metro-container">
        <label class="metro-toggle">
            <input type="checkbox" id="metro-check" checked onchange="toggleMetro()"> 
            🥁 <span id="bpm-val">120</span> BPM
        </label>
        <input type="range" id="bpm-slider" min="40" max="300" value="120" oninput="updateBpm(this.value)">
    </div>

    <div class="dur-controls">
        <div class="dur-btn" id="dur-0.125" onclick="setDur(0.125)">1/8</div>
        <div class="dur-btn" id="dur-0.25" onclick="setDur(0.25)">1/4</div>
        <div class="dur-btn" id="dur-0.5" onclick="setDur(0.5)">1/2</div>
        <div class="dur-btn active" id="dur-1" onclick="setDur(1)">1</div>
        <div class="dur-btn" id="dur-2" onclick="setDur(2)">2</div>
        <div class="dur-btn" id="dur-4" onclick="setDur(4)">4</div>
    </div>
    
    <div class="keyboard-row">
        <div class="key rest" onclick="press('0')">0</div>
        <div class="key" onclick="press('1')">1</div>
        <div class="key" onclick="press('2')">2</div>
        <div class="key" onclick="press('3')">3</div>
        <div class="key" onclick="press('4')">4</div>
        <div class="key" onclick="press('5')">5</div>
        <div class="key" onclick="press('6')">6</div>
        <div class="key" onclick="press('7')">7</div>
        <div class="key octave" onclick="press('8')">8</div>
        <div class="key octave" onclick="press('9')">9</div>
    </div>
    
    <div class="controls">
        <button class="btn btn-play" onclick="playSequence()">▶️</button>
        <button class="btn btn-undo" onclick="undoSeq()">⌫</button>
        <button class="btn btn-clear" onclick="clearSeq()">🗑️</button>
    </div>
</div>

<script>
    function sendMessageToStreamlit(type, data) {
        window.parent.postMessage({ isStreamlitMessage: true, type: type, ...data }, "*");
    }
    
    function sendValueToPython(val) {
        sendMessageToStreamlit("streamlit:setComponentValue", {value: val, dataType: "json"});
    }
    
    function setFrameHeight() {
        // Incrementado a 450px para dar espacio al nuevo panel del metrónomo
        sendMessageToStreamlit("streamlit:setFrameHeight", {height: 450});
    }
    
    sendMessageToStreamlit("streamlit:componentReady", {apiVersion: 1});
    setTimeout(setFrameHeight, 100); 

    // Sintetizador Principal
    const synth = new Tone.PolySynth(Tone.Synth).toDestination();
    
    // Sintetizador para el Metrónomo (estilo Percusión)
    const clickSynth = new Tone.MembraneSynth({
        pitchDecay: 0.01, octaves: 2,
        envelope: { attack: 0.001, decay: 0.1, sustain: 0, release: 0.01 }
    }).toDestination();

    const scale = {"1":"C4", "2":"D4", "3":"E4", "4":"F4", "5":"G4", "6":"A4", "7":"B4", "8":"C5", "9":"D5"};
    
    let sequence = [];
    let currentDur = 1;
    let isPlaying = false;
    
    // Variables del Metrónomo
    let currentBpm = 120;
    let metronomeEnabled = true;

    function updateBpm(val) {
        currentBpm = val;
        document.getElementById("bpm-val").innerText = val;
    }

    function toggleMetro() {
        metronomeEnabled = document.getElementById("metro-check").checked;
    }
    
    // Calcula la duración en segundos de un tiempo (negra) basado en el BPM actual
    function getBeatLength() {
        return 60.0 / currentBpm;
    }

    let isInitialized = false;
    window.addEventListener("message", function(event) {
        if (event.data.type === "streamlit:render") {
            if (!isInitialized) {
                const rawPat = event.data.args.initial_pattern || "";
                if (rawPat) {
                    const tokens = rawPat.replace(/\s+/g, '').split(',');
                    tokens.forEach(tok => {
                        tok = tok.replace(/\|/g, '').replace(/\\n/g, ''); 
                        if(!tok) return;
                        let note = tok;
                        let dur = 1;
                        if(tok.includes('[x')) {
                            let parts = tok.split('[x');
                            note = parts[0];
                            dur = parseFloat(parts[1].replace(']', ''));
                        } else {
                            let dashes = (tok.match(/-/g) || []).length;
                            if (dashes > 0) { dur = 1 + dashes; note = tok.replace(/-/g, ''); }
                        }
                        sequence.push({note: note, dur: dur});
                    });
                }
                updateDisplay();
                isInitialized = true;
            }
            setFrameHeight(); 
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Alt') { e.preventDefault(); setDur(0.125); }
        if (e.key === 'Shift') setDur(0.5);
        if (e.key === 'Control' || e.key === 'Meta') setDur(0.25);
    });
    document.addEventListener('keyup', (e) => {
        if (e.key === 'Alt' || e.key === 'Shift' || e.key === 'Control' || e.key === 'Meta') setDur(1);
    });

    function setDur(val) {
        currentDur = val;
        document.querySelectorAll('.dur-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById('dur-' + val).classList.add('active');
    }

    async function press(note) {
        if (Tone.context.state !== 'running') await Tone.start();
        if (note !== '0') synth.triggerAttackRelease(scale[note], currentDur * getBeatLength());
        sequence.push({note: note, dur: currentDur});
        updateDisplay();
    }

    function undoSeq() { sequence.pop(); updateDisplay(); }
    function clearSeq() { sequence = []; updateDisplay(); }

    function updateDisplay() {
        const displayObj = document.getElementById('display');
        if(sequence.length === 0) { 
            displayObj.innerHTML = "..."; 
            sendValueToPython(""); 
            return; 
        }
        
        let html = "";
        let rawStr = ""; 
        let beatSum = 0;
        let currentGroupDur = null;
        let currentBeat = 0;
        
        for(let i=0; i<sequence.length; i++) {
            let item = sequence[i];
            let itemRaw = item.note;
            
            if (item.dur === 4) itemRaw += "---";
            else if (item.dur === 3) itemRaw += "--";
            else if (item.dur === 2) itemRaw += "-";
            else if (item.dur !== 1) itemRaw += `[x${item.dur}]`;
            
            rawStr += itemRaw;
            let thisNoteStartBeat = Math.floor(beatSum + 0.001);
            beatSum += item.dur;
            beatSum = Math.round(beatSum * 100) / 100;
            
            let isEndOfBar = false;
            if (beatSum >= 4) { isEndOfBar = true; beatSum -= 4; }
            
            if (i < sequence.length - 1) {
                rawStr += ", ";
                if (isEndOfBar) rawStr += "| \\n";
            } else {
                if (isEndOfBar) rawStr += " |";
            }

            if (item.dur < 1) {
                if (currentGroupDur !== item.dur || thisNoteStartBeat !== currentBeat) {
                    if (currentGroupDur !== null) html += "</span>&nbsp;&nbsp;";
                    html += `<span class="dur-${item.dur.toString().replace('.','')}">`;
                    currentGroupDur = item.dur;
                    currentBeat = thisNoteStartBeat;
                } else { html += "&nbsp;"; }
                html += item.note;
            } else {
                if (currentGroupDur !== null) { html += "</span>&nbsp;&nbsp;"; currentGroupDur = null; }
                html += item.note;
                if (item.dur === 4) html += "---";
                if (item.dur === 3) html += "--";
                if (item.dur === 2) html += "-";
                html += "&nbsp;&nbsp;";
                currentBeat = Math.floor(beatSum + 0.001);
            }
            if (isEndOfBar) {
                if (currentGroupDur !== null) { html += "</span>"; currentGroupDur = null; }
                html += " <span class='bar-line'>|</span> <br>";
                currentBeat = 0;
            }
        }
        if (currentGroupDur !== null) html += "</span>";
        
        displayObj.innerHTML = html;
        displayObj.scrollTop = displayObj.scrollHeight;
        
        sendValueToPython(rawStr);
    }

    async function playSequence() {
        if (isPlaying) return; // Evitar que reproduzca múltiples veces simultáneas
        if (Tone.context.state !== 'running') await Tone.start();
        if (sequence.length === 0) return;
        
        isPlaying = true;
        let time = Tone.now() + 0.1; // Pequeño delay para sincronización precisa
        let beatLen = getBeatLength();
        
        // --- Lógica del Metrónomo ---
        if (metronomeEnabled) {
            let totalBeats = 0;
            sequence.forEach(item => totalBeats += item.dur);
            let numClicks = Math.ceil(totalBeats);
            
            for(let b=0; b<numClicks; b++) {
                let isDownbeat = (b % 4 === 0);
                let notePitch = isDownbeat ? "G5" : "G4"; // Acento en el Tiempo 1
                let volume = isDownbeat ? 0.5 : 0.3;
                clickSynth.triggerAttackRelease(notePitch, "32n", time + (b * beatLen), volume);
            }
        }

        // --- Lógica de la Secuencia ---
        sequence.forEach(item => {
            if (item.note !== '0') {
                synth.triggerAttackRelease(scale[item.note], item.dur * beatLen, time);
            }
            time += item.dur * beatLen;
        });

        // Liberar el botón cuando termine la reproducción
        setTimeout(() => { isPlaying = false; }, ((time - Tone.now()) * 1000) + 200);
    }
</script>
</body></html>
"""

with open(os.path.join(_KBD_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(html_code)

_virtual_keyboard_component = components.declare_component("virtual_keyboard", path=_KBD_DIR)

def render_virtual_keyboard(initial_pattern="", key=None):
    return _virtual_keyboard_component(initial_pattern=initial_pattern, key=key, default=initial_pattern)
