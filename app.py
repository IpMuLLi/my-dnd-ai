            
import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re
import time

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="wide", initial_sidebar_state="expanded")

# --- 🎨 UPGRADE GRAFICO (CSS & STILE) ---
st.markdown("""
    <style>
    /* Importazione Font Fantasy 'Cinzel' e 'Lato' */
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@400;700&display=swap');
    
    /* Titoli in stile Fantasy Dorato */
    h1, h2, h3, .stExpander p {
        font-family: 'Cinzel', serif !important;
        color: #DAA520 !important; /* Goldenrod */
        text-shadow: 2px 2px 4px #000000;
    }
    
    /* Nasconde menu standard Streamlit per immersione */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Stile Badge Inventario */
    .inventory-item {
        display: inline-block;
        background-color: #2b2b2b;
        border: 1px solid #DAA520;
        border-radius: 5px;
        padding: 5px 10px;
        margin: 3px;
        font-size: 0.9em;
        color: #e0e0e0;
        font-family: 'Lato', sans-serif;
    }
    
    /* Stile Toast Personalizzato */
    div[data-testid="stToast"] {
        background-color: #1e1e1e !important;
        border: 1px solid #DAA520 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Configurazione API Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

# Recupero chiave Pollinations (Opzionale)
POLL_KEY = st.secrets.get("POLLINATIONS_API_KEY", None)

# CORE MODEL: Gemini 2.5 Flash Lite
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. DATI & REGOLE 5E ---

SKILL_MAP = {
    "Atletica": "Forza", "Furtività": "Destrezza", "Rapidità di mano": "Destrezza", "Acrobazia": "Destrezza",
    "Arcano": "Intelligenza", "Storia": "Intelligenza", "Indagare": "Intelligenza", "Natura": "Intelligenza", "Religione": "Intelligenza",
    "Percezione": "Saggezza", "Intuizione": "Saggezza", "Sopravvivenza": "Saggezza", "Medicina": "Saggezza", "Addestrare Animali": "Saggezza",
    "Persuasione": "Carisma", "Inganno": "Carisma", "Intimidire": "Carisma", "Intrattenere": "Carisma"
}

COMPETENZE_CLASSE = {
    "Guerriero": ["Atletica", "Percezione", "Intimidire"],
    "Mago": ["Arcano", "Storia", "Indagare"],
    "Ladro": ["Furtività", "Rapidità di mano", "Indagare", "Inganno"],
    "Ranger": ["Sopravvivenza", "Percezione", "Natura"],
    "Chierico": ["Religione", "Intuizione", "Storia"]
}

EQUIP_AVANZATO = {
    "Guerriero": ["Cotta di Maglia (CA 16)", "Spada Lunga (1d8)", "Scudo (+2 CA)", "Arco Lungo (1d8)"],
    "Mago": ["Bastone Arcano (1d6)", "Libro Incantesimi", "Vesti del Mago", "Daga (1d4)"],
    "Ladro": ["Daga (1d4) x2", "Arco Corto (1d6)", "Armatura di Cuoio (CA 11)", "Arnesi da Scasso"],
    "Ranger": ["Armatura di Cuoio (CA 11)", "Spada Corta (1d6) x2", "Arco Lungo (1d8)"],
    "Chierico": ["Mazza (1d6)", "Scudo (+2 CA)", "Simbolo Sacro", "Cotta di Maglia (CA 16)"]
}

MAGIE_INIZIALI = {
    "Mago": ["Dardo Incantato", "Mano Magica", "Raggio di Gelo", "Armatura Magica", "Scudo"],
    "Chierico": ["Guida", "Fiamma Sacra", "Cura Ferite", "Dardo Guida", "Benedizione"],
    "Guerriero": [], "Ladro": [], "Ranger": ["Marchio del Cacciatore"]
}

HIT_DICE_MAP = {"Guerriero": 10, "Ranger": 10, "Ladro": 8, "Chierico": 8, "Mago": 6}
XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}
SPELL_SLOTS_TABLE = {1: {1: 2}, 2: {1: 3}, 3: {1: 4, 2: 2}, 4: {1: 4, 2: 3}, 5: {1: 4, 2: 3, 3: 2}}

# --- 2. FUNZIONI TECNICHE ---

def tira_dado(formula):
    try:
        formula = formula.lower().replace(" ", "")
        bonus = 0
        if "+" in formula:
            parts = formula.split("+")
            formula = parts[0]
            bonus = int(parts[1])
        elif "-" in formula:
            parts = formula.split("-")
            formula = parts[0]
            bonus = -int(parts[1])
        if "d" in formula:
            num, faces = map(int, formula.split("d"))
            tiri = [random.randint(1, faces) for _ in range(num)]
            return sum(tiri) + bonus, tiri
        else:
            return int(formula), []
    except: return 0, []

def tira_statistica():
    dadi = [random.randint(1, 6) for _ in range(4)]
    dadi.sort()
    return sum(dadi[1:])

def calcola_mod(punteggio):
    return (punteggio - 10) // 2

def genera_img(descrizione, tipo):
    try:
        seed = random.randint(1, 99999)
        prompt_base = f"Dungeons and Dragons realistic high fantasy, {tipo}: {descrizione}, cinematic lighting, 8k, masterpiece, no text"
        prompt_encoded = urllib.parse.quote(prompt_base)
        base_url = f"https://gen.pollinations.ai/image/{prompt_encoded}"
        params = ["width=1024", "height=1024", f"seed={seed}", "nologo=true", "model=flux"]
        if POLL_KEY: params.append(f"key={POLL_KEY}")
        url = f"{base_url}?{'&'.join(params)}"
        if "gallery" not in st.session_state: st.session_state.gallery = []
        if not st.session_state.gallery or st.session_state.gallery[0]['url'] != url:
            st.session_state.gallery.insert(0, {"url": url, "desc": descrizione})
        return url
    except: return None

def genera_loot(rarita="Comune"):
    tabella = {
        "Comune": ["Pozione di Guarigione", "Pergamena di Dardo Incantato", "Olio per Affilare", "Torcia", "Razioni", "Corda di Seta"],
        "Non Comune": ["Spada +1", "Anello di Protezione", "Mantello del Saltimpalo", "Borsa Conservante", "Stivali Alati"],
        "Raro": ["Armatura di Piastre +1", "Bacchetta delle Palle di Fuoco", "Pozione di Forza del Gigante"]
    }
    # Se rarità è il nome diretto dell'oggetto (fallback)
    if rarita not in tabella:
        scelta = rarita
    else:
        scelta = random.choice(tabella.get(rarita, tabella["Comune"]))
        
    if scelta not in st.session_state.inventario:
        st.session_state.inventario.append(scelta)
        aggiorna_diario(f"Trovato oggetto: {scelta}")
        st.toast(f"Trovato: {scelta}", icon="🎁")
    return scelta

def aggiorna_diario(evento):
    if "journal" not in st.session_state: st.session_state.journal = []
    st.session_state.journal.append(f"- {evento}")
    if len(st.session_state.journal) > 50: st.session_state.journal.pop(0)

def gestisci_memoria():
    if len(st.session_state.messages) > 15:
        st.toast("🧠 Consolidamento memoria...", icon="💾")
        try:
            old_msgs = st.session_state.messages[1:-5]
            txt_to_sum = "\n".join([f"{m['role']}: {m['content']}" for m in old_msgs if m['role'] != 'system'])
            summary_prompt = f"Riassumi i seguenti eventi di D&D in 3 frasi concise mantenendo nomi e fatti chiave:\n{txt_to_sum}"
            summary = model.generate_content(summary_prompt).text
            st.session_state.summary_history += f"\n{summary}"
            st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-5:]
        except Exception as e: print(f"Errore memoria: {e}")

def calcola_ca_avanzata():
    stats = st.session_state.personaggio.get('stats', {})
    mod_des = calcola_mod(stats.get('Destrezza', 10))
    inv = st.session_state.inventario
    ca_base = 10 + mod_des 
    has_heavy, has_medium, has_light = False, False, False
    base_armor = 0
    
    for item in inv:
        if "Cotta di Maglia" in item or "Piastre" in item:
            has_heavy = True
            base_armor = max(base_armor, 16 if "Cotta" in item else 18)
        elif "Giaco di Maglia" in item or "Corazza a Scaglie" in item:
            has_medium = True
            base_armor = max(base_armor, 13 if "Giaco" in item else 14)
        elif "Cuoio" in item:
            has_light = True
            base_armor = max(base_armor, 11) 

    if has_heavy: ca_finale = base_armor
    elif has_medium: ca_finale = base_armor + min(mod_des, 2)
    elif has_light: ca_finale = base_armor + mod_des
    else: ca_finale = 10 + mod_des

    if any("Scudo" in item for item in inv): ca_finale += 2
    if any("Anello di Protezione" in item for item in inv): ca_finale += 1
    st.session_state.ca = ca_finale
# --- 3. STATO INIZIALE ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": [], "magie": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [],
        "spell_slots": {1: 0, 2: 0, 3: 0}, "spell_slots_max": {1: 0, 2: 0, 3: 0},
        "hit_dice_max": 1, "hit_dice_curr": 1, 
        "ultimo_tiro": None, "temp_stats": {}, "ca": 10,
        "nemico_corrente": None,
        "gallery": [], "bestiary": [], "journal": ["- Inizio dell'avventura"],
        "summary_history": "", "pending_action": None
    })

def check_level_up():
    prossimo_liv = XP_LEVELS.get(st.session_state.livello + 1, 999999)
    if st.session_state.xp >= prossimo_liv:
        st.session_state.livello += 1
        st.session_state.bonus_competenza = 2 + ((st.session_state.livello - 1) // 4)
        st.session_state.hit_dice_max = st.session_state.livello
        st.session_state.hit_dice_curr += 1
        aggiorna_diario(f"Level Up! Raggiunto livello {st.session_state.livello}")
        st.toast(f"✨ LIVELLO {st.session_state.livello}!", icon="⚔️")
        p_class = st.session_state.personaggio.get("classe", "")
        if p_class in ["Mago", "Chierico"]:
            slots = SPELL_SLOTS_TABLE.get(st.session_state.livello, {1: 2})
            for lvl, qty in slots.items():
                st.session_state.spell_slots_max[lvl] = qty
                st.session_state.spell_slots[lvl] = qty
        elif p_class == "Ranger" and st.session_state.livello >= 2:
             st.session_state.spell_slots_max[1] = 2
             st.session_state.spell_slots[1] = 2

check_level_up()

# --- 4. SIDEBAR RISTRUTTURATA (GRAFICA) ---
with st.sidebar:
    st.title("🧝 D&D Engine")
    
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        calcola_ca_avanzata()
        if isinstance(st.session_state.spell_slots, int): # Migration Fix
            st.session_state.spell_slots = {1: st.session_state.spell_slots}
            st.session_state.spell_slots_max = {1: st.session_state.spell_slots_max}

        # TAB PRINCIPALI
        main_tabs = st.tabs(["📊 Eroe", "📚 Diario"])
        
        with main_tabs[0]:
            st.subheader(f"{p['nome']}")
            st.caption(f"Lv. {st.session_state.livello} {p['razza']} {p['classe']} | XP: {st.session_state.xp}")
            
            hp_pct = max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max))
            st.write(f"**HP: {st.session_state.hp}/{st.session_state.hp_max}**")
            st.progress(hp_pct)
            
            c_ca, c_hd = st.columns(2)
            c_ca.metric("🛡️ CA", st.session_state.ca)
            c_hd.metric("🎲 Dadi Vita", f"{st.session_state.hit_dice_curr}/{st.session_state.hit_dice_max}")

            st.write("---")
            if st.button("🎲 Tira d20 Puro", use_container_width=True): 
                res = random.randint(1, 20)
                st.session_state.ultimo_tiro = res
                st.session_state.pending_action = f"[DADO PURO: {res}]"
            
            # COMBATTIMENTO
            c1, c2 = st.columns(2)
            with c1:
                weapons_found = []
                for item in st.session_state.inventario:
                    if any(x in item for x in ["Spada", "Mazza", "Ascia", "Martello", "Bastone"]):
                         dice = "1d8" if "Lunga" in item or "Ascia" in item else ("1d4" if "Daga" in item else "1d6")
                         weapons_found.append({"label": item, "stat": "Forza", "dice": dice})
                    elif any(x in item for x in ["Arco", "Daga", "Balestra", "Fionda"]):
                         dice = "1d8" if "Lungo" in item or "Balestra" in item else ("1d4" if "Daga" in item else "1d6")
                         weapons_found.append({"label": item, "stat": "Destrezza", "dice": dice})
                if not weapons_found: weapons_found.append({"label": "Pugno", "stat": "Forza", "dice": "1d4"})
                
                selected_weapon = st.selectbox("Scegli Arma", weapons_found, format_func=lambda x: x["label"].split('(')[0], label_visibility="collapsed")
                if st.button(f"⚔️ Attacca"):
                    mod = calcola_mod(p['stats'][selected_weapon['stat']])
                    tiro_atk = random.randint(1, 20)
                    tot_atk = tiro_atk + mod + st.session_state.bonus_competenza
                    danno, _ = tira_dado(selected_weapon['dice'])
                    danno_tot = max(1, danno + mod)
                    action_str = (f"[AZIONE_COMBAT: Attacco con {selected_weapon['label'].split('(')[0]} | TxC: {tot_atk} | Danni: {danno_tot}]")
                    st.session_state.pending_action = action_str
                    st.session_state.ultimo_tiro = f"Atk: {tot_atk} | Dmg: {danno_tot}"

            with c2:
                rest_type = st.selectbox("Riposo", ["Breve (1 HD)", "Lungo"], label_visibility="collapsed")
                if st.button("💤 Dormi"):
                    if "Lungo" in rest_type:
                        st.session_state.hp = st.session_state.hp_max
                        for k, v in st.session_state.spell_slots_max.items(): st.session_state.spell_slots[k] = v
                        st.session_state.hit_dice_curr = max(1, st.session_state.hit_dice_max // 2)
                        aggiorna_diario("Riposo Lungo completato.")
                        st.session_state.pending_action = "[AZIONE: Riposo Lungo completato]"
                    else: 
                        if st.session_state.hit_dice_curr > 0:
                            dice_face = HIT_DICE_MAP.get(p['classe'], 8)
                            roll = random.randint(1, dice_face)
                            con_mod = calcola_mod(p['stats']['Costituzione'])
                            heal = max(1, roll + con_mod)
                            st.session_state.hp = min(st.session_state.hp_max, st.session_state.hp + heal)
                            st.session_state.hit_dice_curr -= 1
                            aggiorna_diario(f"Riposo Breve: Curati {heal} HP")
                            st.session_state.pending_action = f"[AZIONE: Riposo Breve. Curati {heal} HP.]"
                        else: st.error("Nessun Dado Vita!")

            if st.session_state.ultimo_tiro: st.info(f"Esito: **{st.session_state.ultimo_tiro}**")
            
            sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["Stats", "Skill", "Magia", "Zaino"])
            with sub_tab1:
                for stat, val in p['stats'].items():
                    mod = calcola_mod(val)
                    st.text(f"{stat[:3].upper()}: {val} ({'+' if mod >=0 else ''}{mod})")
            with sub_tab2:
                for skill, stat_ref in SKILL_MAP.items():
                    is_prof = skill in p['competenze']
                    mod_stat = calcola_mod(p['stats'][stat_ref])
                    bonus = mod_stat + (st.session_state.bonus_competenza if is_prof else 0)
                    if st.button(f"{skill} ({'+' if bonus >=0 else ''}{bonus})", key=f"btn_{skill}"):
                        dado = random.randint(1, 20)
                        tot = dado + bonus
                        st.session_state.pending_action = f"[PROVA_ABILITA: {skill} | Totale: {tot}]"
            with sub_tab3: 
                if p['magie']:
                    slot_levs = sorted([k for k,v in st.session_state.spell_slots_max.items() if v > 0])
                    if slot_levs:
                        tabs_lev = st.tabs([f"L{i}" for i in slot_levs] + ["Cantrip"])
                        with tabs_lev[-1]:
                            cantrips = [m for m in p['magie'] if m in ["Guida", "Fiamma Sacra", "Raggio di Gelo", "Mano Magica", "Prestidigitazione"]]
                            for c in cantrips:
                                if st.button(f"✨ {c}", key=f"cast_{c}"): st.session_state.pending_action = f"[LANCIO_INCANTESIMO: {c} (Trucchetto)]"
                        for idx, liv in enumerate(slot_levs):
                            with tabs_lev[idx]:
                                curr, mx = st.session_state.spell_slots.get(liv, 0), st.session_state.spell_slots_max.get(liv, 0)
                                st.write(f"**Slot:** {curr}/{mx}")
                                st.progress(curr/mx if mx > 0 else 0)
                                spells_lev = [m for m in p['magie'] if m not in ["Guida", "Fiamma Sacra", "Raggio di Gelo", "Mano Magica", "Prestidigitazione"]]
                                for s in spells_lev:
                                    if st.button(f"🔮 {s}", key=f"cast_{s}_l{liv}"):
                                        if curr > 0:
                                            st.session_state.spell_slots[liv] -= 1
                                            st.session_state.pending_action = f"[LANCIO_INCANTESIMO: {s} (Slot Liv {liv})]"
                                        else: st.error("Slot esauriti!")
                    else: st.caption("Nessuno slot disponibile.")
                else: st.caption("Nessuna capacità magica.")
            with sub_tab4: # ZAINO GRAFICO (CSS)
                st.write(f"**💰 Oro:** {st.session_state.oro} mo")
                inv_html = ""
                for i in st.session_state.inventario:
                    inv_html += f"<div class='inventory-item'>{i}</div>"
                st.markdown(inv_html, unsafe_allow_html=True)

        with main_tabs[1]:
            st.write("### 📜 Diario")
            if st.session_state.journal:
                for entry in reversed(st.session_state.journal): st.caption(entry)
            st.divider()
            st.write("### 👹 Bestiario")
            if st.session_state.bestiary:
                for b in st.session_state.bestiary: st.error(f"**{b['nome']}** (HP: {b['hp']}/{b['hp_max']})")
        st.divider()
        sd = {k: v for k, v in st.session_state.items() if k != "temp_stats"}
        st.download_button("💾 Salva Eroe", data=json.dumps(sd, default=str), file_name="hero_evolved.json")

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🧙 Legend Engine 2026")
    with st.expander("📂 Carica Personaggio"):
        f = st.file_uploader("Upload .json", type="json")
        if f:
            st.session_state.update(json.load(f))
            st.rerun()

    if not st.session_state.temp_stats:
        if st.button("🎲 Genera Statistiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        st.write("### Risultati dadi")
        cs = st.columns(6)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            mod = calcola_mod(v)
            cs[i].metric(s, f"{v}", f"{'+' if mod >=0 else ''}{mod}")
        if st.button("🔄 Reroll"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()

        with st.form("f_crea"):
            n = st.text_input("Nome")
            r = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            c = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia Avventura"):
                if n:
                    mod_c = calcola_mod(st.session_state.temp_stats["Costituzione"])
                    hd = HIT_DICE_MAP.get(c, 8)
                    hp = hd + mod_c
                    s_max = {1: 0, 2: 0, 3: 0}
                    if c in ["Mago", "Chierico"]: s_max[1] = 2
                    st.session_state.update({
                        "personaggio": {"nome": n, "classe": c, "razza": r, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[c], "magie": MAGIE_INIZIALI[c]},
                        "hp": hp, "hp_max": hp, 
                        "hit_dice_max": 1, "hit_dice_curr": 1,
                        "inventario": EQUIP_AVANZATO[c], "game_phase": "playing",
                        "spell_slots_max": s_max, "spell_slots": s_max.copy()
                    })
                    aggiorna_diario(f"Inizia l'avventura di {n}.")
                    st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                    st.rerun()

else:
    st.title("🛡️ Avventura")
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        p = st.session_state.personaggio
        res = model.generate_content(
            f"Sei il DM. Inizia avventura per {p['nome']} ({p['razza']} {p['classe']}). Descrizione evocativa. Alla fine includi un blocco JSON nascosto per settare la scena."
        ).text
        st.session_state.messages[-1] = {"role": "assistant", "content": res}
        st.rerun()

    # LOGICA AVATAR
    def get_avatar(role):
        if role == "assistant": return "🧙‍♂️"
        pc_class = st.session_state.personaggio.get("classe", "")
        if pc_class == "Guerriero": return "🛡️"
        if pc_class == "Mago": return "🔮"
        if pc_class == "Ladro": return "🗡️"
        if pc_class == "Ranger": return "🏹"
        if pc_class == "Chierico": return "☀️"
        return "👤"

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"], avatar=get_avatar(msg["role"])):
                display_content = re.sub(r'```json.*?```', '', msg["content"], flags=re.DOTALL).strip()
                st.write(display_content)
                if msg.get("image_url"): st.image(msg["image_url"])

    gestisci_memoria()

    prompt = st.chat_input("Cosa fai?")
    input_to_process = st.session_state.pending_action if st.session_state.pending_action else prompt
    st.session_state.pending_action = None 

    if input_to_process:
        display_text = input_to_process.replace("[AZIONE_COMBAT:", "⚔️").replace("[LANCIO_INCANTESIMO:", "✨").replace("]", "")
        st.session_state.messages.append({"role": "user", "content": display_text})
        
        p = st.session_state.personaggio
        journal_str = "\n".join(st.session_state.journal[-10:])
        msgs_to_include = st.session_state.messages[-6:] 
        history_text = st.session_state.summary_history + "\n"
        for m in msgs_to_include:
            if m["role"] != "system":
                c_clean = re.sub(r'```json.*?```', '', m["content"], flags=re.DOTALL).strip()
                history_text += f"{m['role'].upper()}: {c_clean}\n"

        sys = (f"Sei il DM (5e). PG: {p['nome']} {p['classe']}. HP:{st.session_state.hp}/{st.session_state.hp_max}. "
               f"Diario: {journal_str}. Nemico Attivo: {st.session_state.nemico_corrente}. "
               f"\n--- STORIA ---\n{history_text}\n"
               f"--- ISTRUZIONI CRITICHE ---\n"
               f"1. Rispondi narrativamente come un DM esperto.\n"
               f"2. ALLA FINE, INSERISCI BLOCCO JSON PURO PER MECCANICA.\n"
               f"3. FORMATO JSON:\n"
               f"```json\n"
               f"{{\n"
               f"  'enemy_update': {{'name': '...', 'hp': ..., 'ac': ...}} (o null),\n"
               f"  'damage_to_player': int (0 se nullo),\n"
               f"  'xp_gain': int, 'gold_gain': int,\n"
               f"  'loot_found': 'nome_oggetto' (o null),\n"
               f"  'location_visual': 'descrizione per immagine' (o null)\n"
               f"}}\n"
               f"```")
        
        try:
            full_prompt = sys + "\n\nAZIONE: " + input_to_process
            res = model.generate_content(full_prompt).text
            
            img_url = None
            json_match = re.search(r'```json\s*({.*?})\s*```', res, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1).replace("'", '"')) 
                    if data.get("enemy_update"):
                        e_data = data["enemy_update"]
                        st.session_state.nemico_corrente = {"nome": e_data["name"], "hp": e_data["hp"], "hp_max": e_data.get("hp_max", e_data["hp"]), "ca": e_data.get("ac", 10)}
                        if not any(b['nome'] == e_data['name'] for b in st.session_state.bestiary):
                             st.session_state.bestiary.append(st.session_state.nemico_corrente)
                        if st.session_state.nemico_corrente["hp"] <= 0:
                            aggiorna_diario(f"Sconfitto: {st.session_state.nemico_corrente['nome']}")
                            st.session_state.nemico_corrente = None
                            st.toast("Nemico sconfitto!", icon="💀")
                    dmg = data.get("damage_to_player", 0)
                    if dmg > 0:
                        st.session_state.hp = max(0, st.session_state.hp - dmg)
                        aggiorna_diario(f"Subiti {dmg} danni")
                        st.toast(f"-{dmg} HP", icon="🩸")
                    if data.get("xp_gain"): 
                        st.session_state.xp += data["xp_gain"]
                        aggiorna_diario(f"+{data['xp_gain']} XP")
                    if data.get("gold_gain"): st.session_state.oro += data["gold_gain"]
                    if data.get("loot_found"): genera_loot(data["loot_found"]) 
                    if data.get("location_visual"): img_url = genera_img(data["location_visual"], "Scene")
                except Exception as e: print(f"JSON Error: {e}")

            if "[[LUOGO:" in res and not img_url:
                 try: img_url = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Scene")
                 except: pass

            st.session_state.messages.append({"role": "assistant", "content": res, "image_url": img_url})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
        except Exception as e: st.error(f"Errore API: {e}")
                    
