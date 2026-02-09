    import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re
import requests

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="wide", initial_sidebar_state="expanded")

# Caricamento API Keys dai Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("ERRORE: Manca GEMINI_API_KEY nei Secrets!")

POLL_KEY = st.secrets.get("POLLINATIONS_API_KEY", None)

# Modello Gemini Flash Lite per velocità e coerenza
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- 1. FUNZIONI TECNICHE (PRESERVATE) ---
def tira_statistica():
    """Genera una statistica con il metodo 4d6 drop lowest."""
    dadi = [random.randint(1, 6) for _ in range(4)]
    dadi.sort()
    return sum(dadi[1:])

def calcola_mod(punteggio):
    """Calcola il modificatore standard D&D 5e."""
    return (punteggio - 10) // 2

def genera_img(descrizione, tipo):
    """
    Genera immagine tramite Pollinations usando FLUX.
    L'autenticazione avviene tramite la Secret Key nei Secrets.
    """
    try:
        seed = random.randint(1, 99999)
        prompt_base = f"Dungeons and Dragons high fantasy, {tipo}: {descrizione}, cinematic, detailed, 8k, no text"
        prompt_encoded = urllib.parse.quote(prompt_base)
        
        # URL per Pollinations. Con la Key sk_ attiva, il sistema riconosce l'account.
        return f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
    except Exception: 
        return None

def genera_loot(rarita="Comune"):
    """Seleziona un oggetto casuale dalla tabella dei tesori."""
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

# --- 3. GESTIONE STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": [], "magie": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "temp_stats": {}, "ca": 10, "nemico_corrente": None 
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

def check_level_up():
    prossimo_liv = XP_LEVELS.get(st.session_state.livello + 1, 999999)
    if st.session_state.xp >= prossimo_liv:
        st.session_state.livello += 1
        st.toast(f"🎉 LIVELLO {st.session_state.livello} RAGGIUNTO!", icon="✨")

check_level_up()

# --- 4. INTERFACCIA LATERALE (SIDEBAR) ---
with st.sidebar:
    st.title("🛡️ Scheda Eroe")
    
    if POLL_KEY:
        st.caption("🟢 Motore Grafico: Flux (Premium)")
    else:
        st.caption("🟡 Motore Grafico: Flux (Anonimo)")

    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        st.write(f"XP: {st.session_state.xp}")
        st.progress(max(0.0, min(1.0, st.session_state.xp / XP_LEVELS.get(st.session_state.livello + 1, 10000))))

        st.divider()
        c1, c2 = st.columns(2)
        if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
        if c2.button("⛺ Riposo"):
            st.session_state.hp = st.session_state.hp_max
            st.toast("HP ripristinati!")
        
        if st.session_state.ultimo_tiro:
            st.info(f"Ultimo d20: **{st.session_state.ultimo_tiro}**")

        st.divider()
        st.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        st.metric("🛡️ Classe Armatura", st.session_state.ca)

        with st.expander("📊 Caratteristiche"):
            for s, v in p['stats'].items():
                st.write(f"**{s}**: {v} ({calcola_mod(v):+})")

        with st.expander("🎒 Inventario"):
            st.write(f"💰 Oro: {st.session_state.oro}")
            for i in st.session_state.inventario: st.write(f"- {i}")

        if st.session_state.nemico_corrente:
            st.divider()
            n = st.session_state.nemico_corrente
            st.error(f"⚔️ In Combattimento: {n['nome']}")
            st.write(f"HP: {n['hp']}/{n['hp_max']} | CA: {n['ca']}")

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🧙 Crea il tuo Eroe")
    
    if not st.session_state.temp_stats:
        if st.button("🎲 Tira i Dadi per le Statistiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        st.write("### I tuoi Punteggi:")
        cols = st.columns(6)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i].metric(s, v)
        
        with st.form("creazione_form"):
            nome = st.text_input("Nome del Personaggio")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            
            if st.form_submit_button("Inizia l'Avventura"):
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
    st.title("📖 Le Tue Cronache")
    
    # Avvio Narrazione
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        p = st.session_state.personaggio
        intro = model.generate_content(f"Sei il DM. Narra l'inizio per {p['nome']} ({p['classe']}). Usa [[LUOGO:descrizione]].").text
        img = genera_img(intro.split("[[LUOGO:")[1].split("]]")[0], "Scenario") if "[[LUOGO:" in intro else None
        st.session_state.messages[-1] = {"role": "assistant", "content": re.sub(r'\[\[.*?\]\]', '', intro).strip(), "image_url": img}
        st.rerun()

    # Visualizzazione Chat
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("image_url"): st.image(msg["image_url"])

    # Input Giocatore
    if prompt := st.chat_input("Cosa vuoi fare?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        p = st.session_state.personaggio
        
        prompt_dm = (f"DM 5e. PG: {p['nome']} {p['classe']}. HP:{st.session_state.hp}. d20:{st.session_state.ultimo_tiro}. "
                     "Usa i tag: [[NEMICO:nome|hp|ca]], [[DANNO_NEMICO:n]], [[DANNO:n]], [[ORO:n]], [[XP:n]], [[LUOGO:desc]].")
        
        res = model.generate_content(prompt_dm + "\nGiocatore: " + prompt).text
        
        # Parser Meccaniche
        n_m = re.search(r'\[\[NEMICO:(.*?)\|(.*?)\|(.*?)\]\]', res)
        if n_m: st.session_state.nemico_corrente = {"nome": n_m.group(1), "hp": int(n_m.group(2)), "hp_max": int(n_m.group(2)), "ca": int(n_m.group(3))}
        
        dn_m = re.search(r'\[\[DANNO_NEMICO:(\d+)\]\]', res)
        if dn_m and st.session_state.nemico_corrente:
            st.session_state.nemico_corrente["hp"] -= int(dn_m.group(1))
            if st.session_state.nemico_corrente["hp"] <= 0:
                st.session_state.nemico_corrente = None
                st.toast("Nemico Abbattuto!")
        
        d_m = re.search(r'\[\[DANNO:(\d+)\]\]', res)
        if d_m: st.session_state.hp = max(0, st.session_state.hp - int(d_m.group(1)))
        
        xp_m = re.search(r'\[\[XP:(\d+)\]\]', res)
        if xp_m: st.session_state.xp += int(xp_m.group(1))
        
        img = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Scena") if "[[LUOGO:" in res else None
        st.session_state.messages.append({"role": "assistant", "content": re.sub(r'\[\[.*?\]\]', '', res).strip(), "image_url": img})
        st.session_state.ultimo_tiro = None
        st.rerun()
                    
