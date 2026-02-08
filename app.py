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

# Modello aggiornato come da script originale
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. FUNZIONI TECNICHE (PRESERVATE) ---
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

# --- NUOVA FUNZIONE: GENERATORE LOOT DINAMICO ---
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

# --- 2. DATASETS COMPLETI (PRESERVATI & ESPANSI) ---
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

# --- 3. INIZIALIZZAZIONE STATO ---
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
        mod_cos = calcola_mod(st.session_state.personaggio['stats']['Costituzione'])
        dado_vita = 10 if st.session_state.personaggio['classe'] == "Guerriero" else 8
        incremento_hp = random.randint(1, dado_vita) + mod_cos
        st.session_state.hp_max += max(1, incremento_hp)
        st.session_state.hp = st.session_state.hp_max
        if st.session_state.spell_slots_max > 0: st.session_state.spell_slots_max += 1
        st.toast(f"✨ LIVELLO AUMENTATO: Livello {st.session_state.livello}!", icon="⚔️")

check_level_up()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        
        c1, c2 = st.columns(2)
        c1.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        c2.metric("🛡️ CA", st.session_state.ca)

        # --- SEZIONE: NEMICO ---
        if st.session_state.nemico_corrente:
            st.divider()
            st.subheader("⚔️ In Combattimento")
            n = st.session_state.nemico_corrente
            st.warning(f"**{n['nome']}**")
            st.write(f"HP: {n['hp']} | CA: {n['ca']}")
            st.progress(max(0.0, min(1.0, n['hp'] / n['hp_max'])))

        with st.expander("🎒 Inventario & Oro"):
            st.write(f"💰 Oro: **{st.session_state.oro}**")
            for item in st.session_state.inventario: st.write(f"- {item}")

        with st.expander("📊 Abilità (Skills)"):
            for skill, stat_ref in SKILL_MAP.items():
                bonus = calcola_mod(p['stats'].get(stat_ref, 10))
                if skill in p['competenze']:
                    bonus += st.session_state.bonus_competenza
                    st.write(f"🌟 **{skill}**: `{bonus:+}`")
                else:
                    st.write(f"{skill}: `{bonus:+}`")

        with st.expander("🪄 Magie & Stat"):
            for s, v in p['stats'].items(): st.write(f"**{s}**: {v} ({calcola_mod(v):+})")
            st.divider()
            for magia in p.get('magie', []): st.write(f"✨ {magia}")

        with st.expander("🖼️ Galleria"):
            immagini = [m["image_url"] for m in st.session_state.messages if "image_url" in m and m["image_url"]]
            for img_url in immagini[-3:]: st.image(img_url)

        st.divider()
        if st.button("🗑️ Reset Totale"):
            st.session_state.clear()
            st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Officina di Mulli")
    
    if not st.session_state.temp_stats:
        if st.button("🎲 Tira Caratteristiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        with st.form("crea_mulli"):
            nome = st.text_input("Nome dell'Eroe")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia Avventura"):
                mod_cos = calcola_mod(st.session_state.temp_stats["Costituzione"])
                hp_hit_die = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}
                hp_max = hp_hit_die[classe] + mod_cos
                st.session_state.update({
                    "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[classe], "magie": MAGIE_INIZIALI[classe]},
                    "hp": hp_max, "hp_max": hp_max, "inventario": EQUIP_AVANZATO[classe], "game_phase": "playing",
                    "spell_slots_max": 2 if classe in ["Mago", "Chierico"] else 0, "spell_slots_curr": 2 if classe in ["Mago", "Chierico"] else 0
                })
                # Trigger per l'introduzione automatica
                st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                st.rerun()

else:
    st.title("🛡️ Cronache del Destino")
    
    # Check se dobbiamo generare l'introduzione iniziale
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        intro_prompt = (f"Sei il DM di D&D 5e. Presenta l'inizio dell'avventura per un {st.session_state.personaggio['razza']} {st.session_state.personaggio['classe']} "
                        f"di nome {st.session_state.personaggio['nome']}. Descrivi il luogo iniziale usando [[LUOGO:descrizione]].")
        with st.spinner("Il Dungeon Master sta preparando la storia..."):
            res = model.generate_content(intro_prompt).text
            # Gestione Immagine per Intro
            img = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Scena") if "[[LUOGO:" in res else None
            clean_res = re.sub(r'\(.*?\)|\[\[.*?\]\]|DM:', '', res).strip()
            st.session_state.messages[-1] = {"role": "assistant", "content": clean_res, "image_url": img}
            st.rerun()

    # Pulsantiera
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
    if c2.button("⚔️ Attacco"): 
        stat = "Destrezza" if st.session_state.personaggio['classe'] in ["Ladro", "Ranger"] else "Forza"
        st.session_state.ultimo_tiro = random.randint(1, 20) + calcola_mod(st.session_state.personaggio['stats'][stat]) + st.session_state.bonus_competenza
    if c3.button("⛺ Riposo"):
        st.session_state.hp, st.session_state.spell_slots_curr = st.session_state.hp_max, st.session_state.spell_slots_max
        st.success("Riposo completato!")
    if c4.button("🎲 Loot"):
        oggetto = genera_loot("Comune")
        st.toast(f"Hai trovato: {oggetto}!")

    if st.session_state.ultimo_tiro: st.info(f"Ultimo Lancio: **{st.session_state.ultimo_tiro}**")

    # Rendering Chat
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "image_url" in msg and msg["image_url"]: st.image(msg["image_url"])

    # Loop AI
    if prompt := st.chat_input("Cosa fa l'eroe?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # System Prompt arricchito
        sys = (f"Sei il DM 5e. PG: {st.session_state.personaggio}. Ultimo Tiro: {st.session_state.ultimo_tiro}. "
               f"Abilità disponibili per prove: {list(SKILL_MAP.keys())}. "
               f"Usa [[NEMICO:nome|hp|ca]] per nuovi mostri. [[DANNO_NEMICO:n]] per ferirli. "
               f"[[LOOT:rarità]], [[DANNO:n]], [[ORO:n]], [[XP:n]], [[LUOGO:desc]].")
        
        with st.spinner("Il DM sta scrivendo..."):
            res = model.generate_content(sys + "\n" + prompt).text
        
        # --- PARSING MECCANICHE ---
        # Gestione Nemico
        n_m = re.search(r'\[\[NEMICO:(.*?)\|(.*?)\|(.*?)\]\]', res)
        if n_m:
            st.session_state.nemico_corrente = {"nome": n_m.group(1), "hp": int(n_m.group(2)), "hp_max": int(n_m.group(2)), "ca": int(n_m.group(3))}
        
        # Danno al Nemico
        dn_m = re.search(r'\[\[DANNO_NEMICO:(\d+)\]\]', res)
        if dn_m and st.session_state.nemico_corrente:
            st.session_state.nemico_corrente["hp"] -= int(dn_m.group(1))
            if st.session_state.nemico_corrente["hp"] <= 0:
                st.session_state.nemico_corrente = None
                st.toast("Nemico Sconfitto!")

        # Loot automatico
        l_m = re.search(r'\[\[LOOT:(.*?)\]\]', res)
        if l_m: genera_loot(l_m.group(1))

        # Meccaniche standard
        xp_m = re.search(r'\[\[XP:(\d+)\]\]', res)
        if xp_m: st.session_state.xp += int(xp_m.group(1))
        o_m = re.search(r'\[\[ORO:(-?\d+)\]\]', res)
        if o_m: st.session_state.oro = max(0, st.session_state.oro + int(o_m.group(1)))
        d_m = re.search(r'\[\[DANNO:(\d+)\]\]', res)
        if d_m: st.session_state.hp = max(0, st.session_state.hp - int(d_m.group(1)))

        # Generazione Immagine e Pulizia
        clean = re.sub(r'\(.*?\)|\[\[.*?\]\]|DM:', '', res).strip()
        img = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Scena") if "[[LUOGO:" in res else None
        
        st.session_state.messages.append({"role": "assistant", "content": clean, "image_url": img})
        st.session_state.ultimo_tiro = None
        st.rerun()
        
