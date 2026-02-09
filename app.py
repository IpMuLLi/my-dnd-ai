import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="wide", initial_sidebar_state="expanded")

# Caricamento API Keys dai Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("ERRORE: Manca GEMINI_API_KEY nei Secrets!")

POLL_KEY = st.secrets.get("POLLINATIONS_API_KEY", None)

# Modello Gemini Flash Lite
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- 1. FUNZIONI TECNICHE ---
def tira_statistica():
    dadi = [random.randint(1, 6) for _ in range(4)]
    dadi.sort()
    return sum(dadi[1:])

def calcola_mod(punteggio):
    return (punteggio - 10) // 2

def genera_img(descrizione, tipo):
    try:
        seed = random.randint(1, 99999)
        prompt_base = f"Dungeons and Dragons high fantasy, {tipo}: {descrizione}, cinematic, detailed, 8k, no text"
        prompt_encoded = urllib.parse.quote(prompt_base)
        return f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
    except: 
        return None

# --- 2. DATASETS ---
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

# --- 3. GESTIONE STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": [], "magie": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "ca": 10, "nemico_corrente": None, "temp_stats": {}
    })

def aggiorna_ca():
    stats = st.session_state.personaggio.get('stats', {})
    mod_des = calcola_mod(stats.get('Destrezza', 10))
    inv = st.session_state.inventario
    ca_finale = 10 + mod_des
    if any("Cotta di Maglia" in item for item in inv): ca_finale = 16
    elif any("Armatura di Cuoio" in item for item in inv): ca_finale = 11 + mod_des
    if any("Scudo" in item for item in inv): ca_finale += 2
    st.session_state.ca = ca_finale

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        st.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        st.metric("🛡️ CA", st.session_state.ca)
        
        st.divider()
        if st.button("🎲 d20"): 
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.info(f"Risultato: {st.session_state.ultimo_tiro}")
            
        st.divider()
        sd = {k: v for k, v in st.session_state.items() if k != "temp_stats"}
        st.download_button("💾 Salva Eroe", data=json.dumps(sd), file_name="hero.json")

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🧙 Legend Engine 2026")
    
    # --- BLOCCO RIPRISTINATO: CARICAMENTO SALVATAGGIO ---
    with st.expander("📂 Ripristina Eroe (Carica .json)"):
        uploaded_file = st.file_uploader("Scegli un file di salvataggio", type="json")
        if uploaded_file:
            data = json.load(uploaded_file)
            st.session_state.update(data)
            st.success("Salvataggio caricato!")
            st.rerun()
    # ---------------------------------------------------

    st.subheader("Crea un nuovo personaggio")
    if not st.session_state.temp_stats:
        if st.button("🎲 Tira le Statistiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        st.write("Statistiche generate:")
        cols = st.columns(6)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i].metric(s, v)
        
        with st.form("creazione_form"):
            nome = st.text_input("Nome")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia Avventura"):
                if nome:
                    hp_base = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}
                    hp_tot = hp_base[classe] + calcola_mod(st.session_state.temp_stats["Costituzione"])
                    st.session_state.update({
                        "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[classe], "magie": MAGIE_INIZIALI[classe]},
                        "hp": hp_tot, "hp_max": hp_tot, "inventario": EQUIP_AVANZATO[classe], "game_phase": "playing"
                    })
                    st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                    st.rerun()

else:
    st.title("📖 Avventura")
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        p = st.session_state.personaggio
        intro = model.generate_content(f"DM. Narra inizio per {p['nome']} {p['classe']}. Usa [[LUOGO:desc]].").text
        img = genera_img(intro.split("[[LUOGO:")[1].split("]]")[0], "Scenario") if "[[LUOGO:" in intro else None
        st.session_state.messages[-1] = {"role": "assistant", "content": re.sub(r'\[\[.*?\]\]', '', intro).strip(), "image_url": img}
        st.rerun()

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("image_url"): st.image(msg["image_url"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        p = st.session_state.personaggio
        prompt_dm = f"DM 5e. PG: {p['nome']}. HP:{st.session_state.hp}. Usa [[LUOGO:desc]], [[DANNO:n]], [[XP:n]]."
        res = model.generate_content(prompt_dm + "\nGiocatore: " + prompt).text
        
        # Meccaniche veloci
        xp_m = re.search(r'\[\[XP:(\d+)\]\]', res)
        if xp_m: st.session_state.xp += int(xp_m.group(1))
        d_m = re.search(r'\[\[DANNO:(\d+)\]\]', res)
        if d_m: st.session_state.hp = max(0, st.session_state.hp - int(d_m.group(1)))

        img = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Scena") if "[[LUOGO:" in res else None
        st.session_state.messages.append({"role": "assistant", "content": re.sub(r'\[\[.*?\]\]', '', res).strip(), "image_url": img})
        st.rerun()
            
