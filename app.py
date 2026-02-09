import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re
import requests

# --- CONFIGURAZIONE CORE ---
# Impostiamo il layout e il titolo dell'app
st.set_page_config(page_title="D&D Legend Engine 2026", layout="wide", initial_sidebar_state="expanded")

# Configurazione Google Gemini tramite Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

# API Key per Pollinations (Recuperata dai Secrets per evitare Rate Limit)
POLL_KEY = st.secrets.get("POLLINATIONS_API_KEY", None)

# Utilizzo del modello Gemini specificato
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- 1. FUNZIONI TECNICHE ---
def tira_statistica():
    """Genera una statistica con il metodo 4d6 (scarta il più basso)."""
    dadi = [random.randint(1, 6) for _ in range(4)]
    dadi.sort()
    return sum(dadi[1:])

def calcola_mod(punteggio):
    """Calcola il modificatore di caratteristica standard D&D 5e."""
    return (punteggio - 10) // 2

def genera_img(descrizione, tipo):
    """
    Genera immagine usando Pollinations con il modello FLUX.
    Configurato per usare la API Key se presente.
    """
    try:
        seed = random.randint(1, 99999)
        # Prompt ottimizzato per Flux: realismo fantasy cinematografico
        prompt_base = f"Dungeons and Dragons realistic high fantasy, {tipo}: {descrizione}, cinematic lighting, 8k, masterpiece, no text"
        prompt_encoded = urllib.parse.quote(prompt_base)
        
        # Scelta fissa: FLUX per stabilità e qualità
        modello = "flux" 
        
        # Costruzione URL per Pollinations
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&seed={seed}&nologo=true&model={modello}"
        
        return url
    except Exception: 
        return None

def genera_loot(rarita="Comune"):
    """Gestisce la tabella dei tesori e l'aggiunta all'inventario."""
    tabella = {
        "Comune": ["Pozione di Guarigione", "Pergamena di Dardo Incantato", "Olio per Affilare"],
        "Non Comune": ["Spada +1", "Anello di Protezione", "Mantello del Saltimpalo"],
        "Raro": ["Armatura di Piastre +1", "Bacchetta delle Palle di Fuoco", "Pozione di Forza del Gigante"]
    }
    scelta = random.choice(tabella.get(rarita, tabella["Comune"]))
    if scelta not in st.session_state.inventario:
        st.session_state.inventario.append(scelta)
    return scelta

# --- 2. DATASETS ---
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
    "Guerriero": ["Cotta di Maglia (CA 16)", "Spada Lunga", "Scudo (+2 CA)", "Arco Lungo"],
    "Mago": ["Bastone Arcano", "Libro Incantesimi", "Vesti del Mago", "Daga"],
    "Ladro": ["Daga x2", "Arco Corto", "Armatura di Cuoio (CA 11)", "Arnesi da Scasso"],
    "Ranger": ["Armatura di Cuoio (CA 11)", "Spada Corta x2", "Arco Lungo"],
    "Chierico": ["Mazza", "Scudo (+2 CA)", "Simbolo Sacro", "Cotta di Maglia (CA 16)"]
}

MAGIE_INIZIALI = {
    "Mago": ["Dardo Incantato", "Mano Magica", "Prestidigitazione", "Armatura Magica"],
    "Chierico": ["Guida", "Fiamma Sacra", "Cura Ferite", "Dardo Guida"],
    "Guerriero": [], "Ladro": [], "Ranger": []
}

XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}

# --- 3. STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": [], "magie": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "temp_stats": {}, "ca": 10, "event_log": [],
        "nemico_corrente": None 
    })

def aggiorna_ca():
    """Ricalcola la CA basata su equipaggiamento e Destrezza."""
    stats = st.session_state.personaggio.get('stats', {})
    mod_des = calcola_mod(stats.get('Destrezza', 10))
    inv = st.session_state.inventario
    ca_finale = 10 + mod_des
    if any("Cotta di Maglia" in item for item in inv): ca_finale = 16
    elif any("Armatura di Cuoio" in item for item in inv): ca_finale = 11 + mod_des
    if any("Scudo" in item for item in inv): ca_finale += 2
    st.session_state.ca = ca_finale

def check_level_up():
    """Verifica se l'eroe ha guadagnato abbastanza XP per livellare."""
    prossimo_liv = XP_LEVELS.get(st.session_state.livello + 1, 999999)
    if st.session_state.xp >= prossimo_liv:
        st.session_state.livello += 1
        st.toast(f"✨ LIVELLO {st.session_state.livello}!", icon="⚔️")

check_level_up()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    
    if POLL_KEY:
        st.success("✅ API Pollinations Attiva")
    else:
        st.warning("⚠️ Usando Pollinations senza Key (Rate Limit possibile)")

    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        
        # BARRA XP
        xp_max = XP_LEVELS.get(st.session_state.livello + 1, st.session_state.xp + 1000)
        st.write(f"✨ XP: {st.session_state.xp} / {xp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.xp / xp_max)))

        # AZIONI FISSE
        st.divider()
        c1, c2 = st.columns(2)
        if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
        if c2.button("⚔️ Attacco"): 
            stat = "Destrezza" if p['classe'] in ["Ladro", "Ranger"] else "Forza"
            tiro = random.randint(1, 20)
            mod = calcola_mod(p['stats'][stat])
            st.session_state.ultimo_tiro = tiro + mod + st.session_state.bonus_competenza
        
        c3, c4 = st.columns(2)
        if c3.button("⛺ Riposo"):
            st.session_state.hp = st.session_state.hp_max
            st.session_state.spell_slots_curr = st.session_state.spell_slots_max
            st.toast("Riposo completato!")
        if c4.button("🎁 Loot"): genera_loot()

        if st.session_state.ultimo_tiro:
            st.info(f"Ultimo Risultato: **{st.session_state.ultimo_tiro}**")

        # STATISTICHE VITALI
        st.divider()
        col_hp, col_ca = st.columns(2)
        col_hp.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        col_ca.metric("🛡️ CA", st.session_state.ca)

        # CARATTERISTICHE
        st.write("### 📊 Caratteristiche")
        cols_stats = st.columns(3)
        stats_list = list(p['stats'].items())
        for i in range(6):
            s, v = stats_list[i]
            cols_stats[i%3].write(f"**{s[:3]}**: {v}\n({calcola_mod(v):+})")

        # BESTIARIO
        if st.session_state.nemico_corrente:
            st.divider()
            n = st.session_state.nemico_corrente
            st.error(f"⚔️ **{n['nome']}**")
            st.write(f"HP: {n['hp']} | CA: {n['ca']}")
            st.progress(max(0.0, min(1.0, n['hp'] / n['hp_max'])))

        # INVENTARIO
        with st.expander("🎒 Inventario & Oro"):
            st.write(f"💰 Oro: {st.session_state.oro}")
            for i in st.session_state.inventario: st.write(f"- {i}")

        st.divider()
        sd = {k: v for k, v in st.session_state.items() if k != "temp_stats"}
        st.download_button("💾 Salva Personaggio", data=json.dumps(sd), file_name="hero.json")

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Creazione Eroe")
    
    with st.expander("📂 Carica Salvataggio"):
        f = st.file_uploader("Carica file .json", type="json")
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
            cs[i].metric(s, v)
        
        with st.form("f_crea"):
            n = st.text_input("Nome")
            r = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            c = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia Avventura"):
                if n:
                    mod_c = calcola_mod(st.session_state.temp_stats["Costituzione"])
                    hd = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}
                    hp = hd[c] + mod_c
                    st.session_state.update({
                        "personaggio": {"nome": n, "classe": c, "razza": r, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[c], "magie": MAGIE_INIZIALI[c]},
                        "hp": hp, "hp_max": hp, "inventario": EQUIP_AVANZATO[c], "game_phase": "playing",
                        "spell_slots_max": 2 if c in ["Mago", "Chierico"] else 0, "spell_slots_curr": 2 if c in ["Mago", "Chierico"] else 0
                    })
                    st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                    st.rerun()

else:
    st.title("🛡️ Cronache dell'Avventura")
    
    # Intro
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        p = st.session_state.personaggio
        res = model.generate_content(f"DM 5e. Inizia avventura per {p['nome']} ({p['classe']}). Usa [[LUOGO:desc]].").text
        img = None
        if "[[LUOGO:" in res:
            desc = res.split("[[LUOGO:")[1].split("]]")[0]
            img = genera_img(desc, "Scena")
        st.session_state.messages[-1] = {"role": "assistant", "content": re.sub(r'\[\[.*?\]\]', '', res).strip(), "image_url": img}
        st.rerun()

    # History
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("image_url"): st.image(msg["image_url"])

    # Input
    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        p = st.session_state.personaggio
        sys = (f"DM 5e. PG: {p['nome']} {p['classe']}. HP:{st.session_state.hp}/{st.session_state.hp_max}. Dado:{st.session_state.ultimo_tiro}. "
               "Usa: [[NEMICO:nome|hp|ca]], [[DANNO_NEMICO:n]], [[LOOT:rarità]], [[DANNO:n]], [[ORO:n]], [[XP:n]], [[LUOGO:desc]].")
        res = model.generate_content(sys + "\n" + prompt).text
        
        # Meccaniche parser
        n_m = re.search(r'\[\[NEMICO:(.*?)\|(.*?)\|(.*?)\]\]', res)
        if n_m: st.session_state.nemico_corrente = {"nome": n_m.group(1), "hp": int(n_m.group(2)), "hp_max": int(n_m.group(2)), "ca": int(n_m.group(3))}
        
        dn_m = re.search(r'\[\[DANNO_NEMICO:(\d+)\]\]', res)
        if dn_m and st.session_state.nemico_corrente:
            st.session_state.nemico_corrente["hp"] -= int(dn_m.group(1))
            if st.session_state.nemico_corrente["hp"] <= 0: st.session_state.nemico_corrente = None
        
        d_m = re.search(r'\[\[DANNO:(\d+)\]\]', res)
        if d_m: st.session_state.hp = max(0, st.session_state.hp - int(d_m.group(1)))
        
        xp_m = re.search(r'\[\[XP:(\d+)\]\]', res)
        if xp_m: st.session_state.xp += int(xp_m.group(1))
        
        o_m = re.search(r'\[\[ORO:(-?\d+)\]\]', res)
        if o_m: st.session_state.oro = max(0, st.session_state.oro + int(o_m.group(1)))

        img = None
        if "[[LUOGO:" in res:
            desc = res.split("[[LUOGO:")[1].split("]]")[0]
            img = genera_img(desc, "Scena")
        
        st.session_state.messages.append({"role": "assistant", "content": re.sub(r'\[\[.*?\]\]', '', res).strip(), "image_url": img})
        st.session_state.ultimo_tiro = None
        st.rerun()
