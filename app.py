import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="wide", initial_sidebar_state="expanded")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

model = genai.GenerativeModel('gemini-2.0-flash')

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
        prompt_base = f"Dungeons and Dragons realistic high fantasy, {tipo}: {descrizione}, cinematic lighting, 8k, masterpiece, no text"
        prompt_encoded = urllib.parse.quote(prompt_base)
        return f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
    except: return None

def genera_loot(rarita="Comune"):
    tabella = {
        "Comune": ["Pozione di Guarigione", "Pergamena di Dardo Incantato", "Olio per Affilare"],
        "Non Comune": ["Spada +1", "Anello di Protezione", "Mantello del Saltimpalo"],
        "Raro": ["Armatura di Piastre +1", "Bacchetta delle Palle di Fuoco", "Pozione di Forza del Gigante"]
    }
    scelta = random.choice(tabella.get(rarita, tabella["Comune"]))
    if scelta not in st.session_state.inventario:
        st.session_state.inventario.append(scelta)
    return scelta

# --- FUNZIONE DI PARSING EVOLUTA (Risolve il bug del testo mancante) ---
def processa_risposta_dm(testo_raw):
    """
    Estrae i dati dai tag e pulisce il testo per la chat.
    Reintegra il nome del nemico nel testo leggibile invece di cancellarlo.
    """
    testo_lavoro = testo_raw
    
    # Gestione Nemico: Estrae i dati e sostituisce il tag col solo Nome
    n_m = re.search(r'\[\[NEMICO:(.*?)\|(.*?)\|(.*?)\]\]', testo_lavoro)
    if n_m:
        nome_nemico = n_m.group(1)
        st.session_state.nemico_corrente = {
            "nome": nome_nemico, 
            "hp": int(n_m.group(2)), 
            "hp_max": int(n_m.group(2)), 
            "ca": int(n_m.group(3))
        }
        # Invece di cancellare tutto, lasciamo il nome del nemico nel testo
        testo_lavoro = testo_lavoro.replace(n_m.group(0), f"**{nome_nemico}**")

    # Danno al Nemico
    dn_m = re.search(r'\[\[DANNO_NEMICO:(\d+)\]\]', testo_lavoro)
    if dn_m and st.session_state.nemico_corrente:
        st.session_state.nemico_corrente["hp"] -= int(dn_m.group(1))
        if st.session_state.nemico_corrente["hp"] <= 0:
            st.session_state.nemico_corrente = None
    
    # Altre meccaniche (XP, Oro, Danno al PG)
    xp_m = re.search(r'\[\[XP:(\d+)\]\]', testo_lavoro)
    if xp_m: st.session_state.xp += int(xp_m.group(1))
    
    o_m = re.search(r'\[\[ORO:(-?\d+)\]\]', testo_lavoro)
    if o_m: st.session_state.oro = max(0, st.session_state.oro + int(o_m.group(1)))
    
    d_m = re.search(r'\[\[DANNO:(\d+)\]\]', testo_lavoro)
    if d_m: st.session_state.hp = max(0, st.session_state.hp - int(d_m.group(1)))

    # Immagine Luogo
    img = None
    if "[[LUOGO:" in testo_lavoro:
        desc_luogo = testo_lavoro.split("[[LUOGO:")[1].split("]]")[0]
        img = genera_img(desc_luogo, "Scena")

    # Pulizia finale di ogni tag residuo per non sporcare la UI
    testo_finale = re.sub(r'\[\[.*?\]\]', '', testo_lavoro).strip()
    return testo_finale, img

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
        st.toast(f"✨ LIVELLO {st.session_state.livello}!", icon="⚔️")

check_level_up()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        
        xp_max = XP_LEVELS.get(st.session_state.livello + 1, st.session_state.xp + 1000)
        st.write(f"✨ XP: {st.session_state.xp} / {xp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.xp / xp_max)))

        st.divider()
        c1, c2 = st.columns(2)
        if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
        if c2.button("⚔️ Attacco"): 
            stat = "Destrezza" if p['classe'] in ["Ladro", "Ranger"] else "Forza"
            st.session_state.ultimo_tiro = random.randint(1, 20) + calcola_mod(p['stats'][stat]) + st.session_state.bonus_competenza
        
        c3, c4 = st.columns(2)
        if c3.button("⛺ Riposo"):
            st.session_state.hp = st.session_state.hp_max
            st.session_state.spell_slots_curr = st.session_state.spell_slots_max
            st.toast("Riposo completato!")
        if c4.button("🎁 Loot"): genera_loot()

        if st.session_state.ultimo_tiro:
            st.info(f"Ultimo Tiro: **{st.session_state.ultimo_tiro}**")

        st.divider()
        col_hp, col_ca = st.columns(2)
        col_hp.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        col_ca.metric("🛡️ CA", st.session_state.ca)

        st.write("### 📊 Caratteristiche")
        cols_stats = st.columns(3)
        stats_list = list(p['stats'].items())
        for i in range(6):
            s, v = stats_list[i]
            cols_stats[i%3].write(f"**{s[:3]}**: {v}\n({calcola_mod(v):+})")

        if p['magie']:
            st.divider()
            st.write("### 🪄 Magie")
            if st.session_state.spell_slots_max > 0:
                st.write(f"Slot: {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
            for m in p['magie']:
                st.caption(f"✨ {m}")

        if st.session_state.nemico_corrente:
            st.divider()
            n = st.session_state.nemico_corrente
            st.error(f"⚔️ **{n['nome']}**")
            st.write(f"HP: {n['hp']} | CA: {n['ca']}")
            st.progress(max(0.0, min(1.0, n['hp'] / n['hp_max'])))

        with st.expander("🎒 Inventario & Oro"):
            st.write(f"💰 Oro: {st.session_state.oro}")
            for i in st.session_state.inventario: st.write(f"- {i}")

        with st.expander("🌟 Abilità"):
            for sk, st_ref in SKILL_MAP.items():
                b = calcola_mod(p['stats'].get(st_ref, 10))
                if sk in p['competenze']: b += st.session_state.bonus_competenza
                st.write(f"{'●' if sk in p['competenze'] else '○'} {sk}: {b:+}")

        st.divider()
        sd = {k: v for k, v in st.session_state.items() if k != "temp_stats"}
        st.download_button("💾 Salva", data=json.dumps(sd), file_name="hero.json")

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Creazione Eroe")
    
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
            cs[i].metric(s, v)
        
        if st.button("🔄 Reroll"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()

        with st.form("f_crea"):
            n = st.text_input("Nome")
            r = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            c = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia"):
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
    st.title("🛡️ Avventura")
    
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        p = st.session_state.personaggio
        res_raw = model.generate_content(f"DM 5e. Inizia avventura per {p['nome']} ({p['classe']}). Usa i tag come [[LUOGO:desc]] e [[NEMICO:nome|hp|ca]].").text
        testo, img = processa_risposta_dm(res_raw)
        st.session_state.messages[-1] = {"role": "assistant", "content": testo, "image_url": img}
        st.rerun()

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("image_url"): st.image(msg["image_url"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        p = st.session_state.personaggio
        sys = (f"Sei il DM di D&D 5e. PG: {p['nome']} ({p['classe']}). HP:{st.session_state.hp}. Ultimo Dado:{st.session_state.ultimo_tiro}. "
               f"Se inserisci un nemico, scrivi il tag [[NEMICO:Nome|HP|CA]] proprio nel punto della frase dove deve apparire il nome. "
               f"Tag: [[NEMICO:nome|hp|ca]], [[DANNO_NEMICO:n]], [[LOOT:rarità]], [[DANNO:n]], [[ORO:n]], [[XP:n]], [[LUOGO:desc]].")
        
        res_raw = model.generate_content(sys + "\n" + prompt).text
        testo, img = processa_risposta_dm(res_raw)
        
        st.session_state.messages.append({"role": "assistant", "content": testo, "image_url": img})
        st.session_state.ultimo_tiro = None
        st.rerun()
        
