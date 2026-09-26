import json
import streamlit.components.v1 as components

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
                
                // 1. Lógica de Nota en tiempo real
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
                
                // 2. Lógica de "Top Repetición" (Muestra la nota desde el puente preparatorio)
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

def render_virtual_keyboard(initial_pattern=""):
    safe_pattern = json.dumps(initial_pattern)
    
    html_keyboard = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/combine/npm/tone@14.7.58"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; padding: 5px; font-family: sans-serif; background: #121212; color: white; display: flex; flex-direction: column; align-items: center; }}
        
        .dur-controls {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-bottom: 8px; width: 100%; max-width: 350px; }}
        .dur-btn {{ background: #222; border: 1px solid #555; color: white; padding: 6px 0px; border-radius: 4px; cursor: pointer; text-align: center; font-size: 0.75rem; transition: 0.1s; user-select: none; }}
        .dur-btn.active {{ background: #00BFFF; color: black; font-weight: bold; border-color: #008CBA; transform: scale(1.05); }}
        
        .screen {{ 
            background: #000; border: 2px solid #444; border-radius: 6px; 
            width: 100%; max-width: 350px; padding: 10px; 
            min-height: 60px; max-height: 120px;
            overflow-y: auto; 
            font-family: monospace; font-size: 1rem; color: #00ff00; 
            margin-bottom: 8px; white-space: normal; line-height: 2; 
        }}
        
        .screen::-webkit-scrollbar {{ width: 6px; }}
        .screen::-webkit-scrollbar-thumb {{ background-color: #555; border-radius: 3px; }}
        
        .dur-05 {{ display: inline-block; border-bottom: 2px solid #00ff00; padding-bottom: 1px; }}
        .dur-025 {{ display: inline-block; border-bottom: 4px double #00ff00; padding-bottom: 1px; }}
        .dur-0125 {{ display: inline-block; position: relative; border-bottom: 2px solid #00ff00; padding-bottom: 1px; }}
        .dur-0125::after {{ content: ''; position: absolute; left: 0; right: 0; bottom: -4px; border-bottom: 4px double #00ff00; }}
        
        .bar-line {{ color: #777; margin: 0 4px; font-weight: bold; }}
        
        .keyboard {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; width: 100%; max-width: 350px; margin-bottom: 10px; }}
        .key {{ background: #333; border: 2px solid #555; border-radius: 6px; padding: 8px 0; font-size: 1rem; font-weight: bold; color: white; cursor: pointer; text-align: center; transition: 0.1s; user-select: none; display: flex; align-items: center; justify-content: center; }}
        .key:active {{ background: #FFD700; color: black; transform: scale(0.95); }}
        .key.rest {{ background: #1a4b6e; border-color: #2a7baf; font-size: 0.8rem; }}
        .key.octave {{ background: #4a1a6e; border-color: #7a2aaf; }}
        .key.modifier {{ background: #444; border-color: #666; color: #f39c12; font-size: 0.9rem; }}
        
        .controls {{ display: flex; gap: 8px; width: 100%; max-width: 350px; }}
        .btn {{ flex: 1; padding: 10px; font-size: 0.9rem; font-weight: bold; border-radius: 6px; border: none; cursor: pointer; color: white; }}
        .btn-play {{ background: #28a745; }}
        .btn-undo {{ background: #fd7e14; }}
        .btn-clear {{ background: #dc3545; }}
    </style>
    </head><body>
    
    <div class="dur-controls">
        <div class="dur-btn" id="dur-0.125" onclick="setDur(0.125)">1/8 (Alt)</div>
        <div class="dur-btn" id="dur-0.25" onclick="setDur(0.25)">1/4 (Ctrl)</div>
        <div class="dur-btn" id="dur-0.5" onclick="setDur(0.5)">1/2 (Shft)</div>
        <div class="dur-btn active" id="dur-1" onclick="setDur(1)">1</div>
        <div class="dur-btn" id="dur-2" onclick="setDur(2)">2</div>
        <div class="dur-btn" id="dur-4" onclick="setDur(4)">4</div>
        <div class="dur-btn" id="dur-6" onclick="setDur(6)">6</div>
        <div class="dur-btn" id="dur-8" onclick="setDur(8)">8</div>
        <div class="dur-btn" id="dur-12" onclick="setDur(12)">12</div>
    </div>
    
    <div class="screen" id="display">...</div>
    
    <div class="keyboard">
        <div class="key" onclick="press('1')">1</div>
        <div class="key" onclick="press('2')">2</div>
        <div class="key" onclick="press('3')">3</div>
        <div class="key" onclick="press('4')">4</div>
        <div class="key" onclick="press('5')">5</div>
        <div class="key" onclick="press('6')">6</div>
        <div class="key" onclick="press('7')">7</div>
        <div class="key octave" onclick="press('8')">8</div>
        <div class="key octave" onclick="press('9')">9</div>
        <div class="key octave" onclick="press('10')">10</div>
        <div class="key octave" onclick="press('11')">11</div>
        <div class="key octave" onclick="press('12')">12</div>
        <div class="key octave" onclick="press('13')">13</div>
        <div class="key octave" onclick="press('14')">14</div>
        <div class="key octave" onclick="press('15')">15</div>
        <div class="key rest" onclick="press('0')">Sil. (0)</div>
        
        <!-- BOTONES DE ALTERACIÓN -->
        <div class="key modifier" style="grid-column: span 2;" onclick="modifyLast('#')">Sostenido (#)</div>
        <div class="key modifier" style="grid-column: span 2;" onclick="modifyLast('b')">Bemol (b)</div>
    </div>
    
    <div class="controls">
        <button class="btn btn-play" onclick="playSequence()">▶️</button>
        <button class="btn btn-undo" onclick="undoSeq()">⌫ Atrás</button>
        <button class="btn btn-clear" onclick="clearSeq()">🗑️ Todo</button>
    </div>
    
    <div style="width: 100%; max-width: 350px; margin-top: 15px; text-align: center;">
        <p style="font-size: 0.8rem; color: #bbb; margin: 0 0 5px 0;">👇 Toca el recuadro para copiar el patrón 👇</p>
        <textarea id="raw-output" readonly rows="2"
               style="width: 100%; padding: 10px; font-size: 1rem; border-radius: 6px; border: 2px dashed #007bff; background: #1a1a1a; color: #fff; text-align: center; cursor: pointer; outline: none; resize: none;"
               onclick="selectAndCopy(this)">...</textarea>
    </div>

    <script>
        const synth = new Tone.PolySynth(Tone.Synth).toDestination();
        const scale = {{
            "1":"C4", "2":"D4", "3":"E4", "4":"F4", "5":"G4", "6":"A4", "7":"B4", 
            "8":"C5", "9":"D5", "10":"E5", "11":"F5", "12":"G5", "13":"A5", "14":"B5", "15":"C6"
        }};
        let sequence = [];
        let currentDur = 1;
        const rawPat = {safe_pattern};

        async function initTone() {{ if (Tone.context.state !== 'running') await Tone.start(); }}

        // LÓGICA PARA TRADUCIR NOTAS CON ALTERACIONES AL SINTETIZADOR
        function getToneNote(noteStr) {{
            if (noteStr === '0') return null;
            let base = noteStr.replace(/[#b]/g, '');
            let pitch = scale[base]; 
            if (!noteStr.includes('#') && !noteStr.includes('b')) return pitch;
            
            let pitchClass = pitch.slice(0, -1);
            let octave = parseInt(pitch.slice(-1));
            const allNotes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
            let idx = allNotes.indexOf(pitchClass);
            
            if (noteStr.includes('#')) {{
                idx++;
                if (idx > 11) {{ idx = 0; octave++; }}
            }} else if (noteStr.includes('b')) {{
                idx--;
                if (idx < 0) {{ idx = 11; octave--; }}
            }}
            return allNotes[idx] + octave;
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Alt') {{ e.preventDefault(); setDur(0.125); }}
            if (e.key === 'Shift') setDur(0.5);
            if (e.key === 'Control' || e.key === 'Meta') setDur(0.25);
        }});
        document.addEventListener('keyup', (e) => {{
            if (e.key === 'Alt' || e.key === 'Shift' || e.key === 'Control' || e.key === 'Meta') setDur(1);
        }});

        function setDur(val) {{
            currentDur = val;
            document.querySelectorAll('.dur-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('dur-' + val).classList.add('active');
        }}

        async function press(note) {{
            await initTone();
            if (note !== '0') {{
                let toneDur = (currentDur * 0.5) + "s";
                synth.triggerAttackRelease(getToneNote(note), toneDur);
            }}
            sequence.push({{note: note, dur: currentDur}});
            updateDisplay();
        }}

        // NUEVA FUNCIÓN PARA APLICAR ALTERACIONES
        async function modifyLast(accidental) {{
            if (sequence.length === 0) return;
            let lastItem = sequence[sequence.length - 1];
            if (lastItem.note === '0') return; // No se puede alterar un silencio
            
            let baseNote = lastItem.note.replace(/[#b]/g, '');
            
            // Si presionas la misma alteración, la quita (Toggle). Si no, la aplica.
            if (lastItem.note.endsWith(accidental)) {{
                lastItem.note = baseNote;
            }} else {{
                lastItem.note = baseNote + accidental;
            }}
            
            // Reproducir la nota ya alterada
            await initTone();
            let toneDur = (lastItem.dur * 0.5) + "s";
            synth.triggerAttackRelease(getToneNote(lastItem.note), toneDur);
            
            updateDisplay();
        }}

        function undoSeq() {{ sequence.pop(); updateDisplay(); }}
        function clearSeq() {{ sequence = []; updateDisplay(); }}

        function updateDisplay() {{
            const displayObj = document.getElementById('display');
            const rawOutputObj = document.getElementById('raw-output');
            
            if(sequence.length === 0) {{ 
                displayObj.innerHTML = "..."; 
                displayObj.dataset.raw = ""; 
                rawOutputObj.value = "...";
                return; 
            }}
            
            let html = "";
            let rawStr = ""; 
            let beatSum = 0;
            let currentGroupDur = null;
            
            for(let i=0; i<sequence.length; i++) {{
                let item = sequence[i];
                
                let itemRaw = item.note;
                if (item.dur === 4) itemRaw += "---";
                else if (item.dur === 3) itemRaw += "--";
                else if (item.dur === 2) itemRaw += "-";
                else if (item.dur !== 1) itemRaw += `[x${{item.dur}}]`;
                
                rawStr += itemRaw;
                beatSum += item.dur;
                beatSum = Math.round(beatSum * 100) / 100;
                
                let isEndOfBar = false;
                if (beatSum >= 4) {{ isEndOfBar = true; beatSum -= 4; }}
                
                if (i < sequence.length - 1) {{
                    rawStr += ", ";
                    if (isEndOfBar) rawStr += "| \\n";
                }} else {{
                    if (isEndOfBar) rawStr += " |";
                }}

                if (item.dur < 1) {{
                    if (currentGroupDur !== item.dur) {{
                        if (currentGroupDur !== null) html += "</span>&nbsp;";
                        html += `<span class="dur-${{item.dur.toString().replace('.','')}}">`;
                        currentGroupDur = item.dur;
                    }} else {{ html += "&nbsp;&nbsp;"; }}
                    html += item.note;
                }} else {{
                    if (currentGroupDur !== null) {{ html += "</span>&nbsp;&nbsp;"; currentGroupDur = null; }}
                    html += item.note;
                    if (item.dur === 4) html += "---";
                    else if (item.dur === 3) html += "--";
                    else if (item.dur === 2) html += "-";
                    else if (item.dur > 4) html += `<small>[x${{item.dur}}]</small>`;
                    html += "&nbsp;&nbsp;";
                }}
                
                if (isEndOfBar) {{
                    if (currentGroupDur !== null) {{ html += "</span>"; currentGroupDur = null; }}
                    html += " <span class='bar-line'>|</span> <br>";
                }}
            }}
            if (currentGroupDur !== null) html += "</span>";
            
            displayObj.innerHTML = html;
            displayObj.dataset.raw = rawStr;
            rawOutputObj.value = rawStr;
            
            displayObj.scrollTop = displayObj.scrollHeight;
        }}

        async function playSequence() {{
            await initTone();
            if (sequence.length === 0) return;
            let time = Tone.now();
            sequence.forEach(item => {{
                if (item.note !== '0') {{
                    let toneDur = (item.dur * 0.5) + "s";
                    synth.triggerAttackRelease(getToneNote(item.note), toneDur, time);
                }}
                time += item.dur * 0.5;
            }});
        }}

        function selectAndCopy(el) {{
            if (!el.value || el.value === "...") return;
            el.focus();
            el.select();
            el.setSelectionRange(0, 99999); 
            
            try {{
                if (navigator.clipboard && window.isSecureContext) {{
                    navigator.clipboard.writeText(el.value);
                }} else {{
                    document.execCommand('copy');
                }}
                
                const originalBorder = el.style.border;
                el.style.border = "2px solid #28a745";
                el.style.color = "#28a745";
                setTimeout(() => {{
                    el.style.border = originalBorder;
                    el.style.color = "#fff";
                }}, 1000);
                
            }} catch (err) {{}}
        }}

        if (rawPat) {{
            const tokens = rawPat.replace(/\\s+/g, '').split(',');
            tokens.forEach(tok => {{
                tok = tok.replace(/\\|/g, ''); 
                if(!tok) return;
                let note = tok;
                let dur = 1;
                
                if(tok.includes('[x')) {{
                    let parts = tok.split('[x');
                    note = parts[0];
                    dur = parseFloat(parts[1].replace(']', ''));
                }} else {{
                    let dashes = (tok.match(/-/g) || []).length;
                    if (dashes > 0) {{
                        dur = 1 + dashes;
                        note = tok.replace(/-/g, '');
                    }}
                }}
                sequence.push({{note: note, dur: dur}});
            }});
            updateDisplay();
        }}
    </script>
    </body></html>
    """
    components.html(html_keyboard, height=660)
