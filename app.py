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

# --- 2. DATASETS COMPLETI ---
SKILL_MAP = {
    "Atletica": "Forza", "Furtività": "Destrezza", "Rapidità di mano": "Destrezza",
    "Arcano": "Intelligenza", "Storia": "Intelligenza", "Indagare": "Intelligenza",
    "Percezione": "Saggezza", "Intuizione": "Saggezza", "Sopravvivenza": "Saggezza",
    "Persuasione": "Carisma", "Religione": "Intelligenza", "Natura": "Intelligenza"
}

COMPETENZE_CLASSE = {
    "Guerriero": ["Atletica", "Percezione"],
    "Mago": ["Arcano", "Storia"],
    "Ladro": ["Furtività", "Rapidità di mano", "Indagare"],
    "Ranger": ["Sopravvivenza", "Percezione", "Natura"],
    "Chierico": ["Religione", "Intuizione"]
}

EQUIP_AVANZATO = {
    "Guerriero": ["Cotta di Maglia (CA 16)", "Spada Lunga", "Scudo", "Arco Lungo"],
    "Mago": ["Bastone Arcano", "Libro Incantesimi", "Borsa Componenti"],
    "Ladro": ["Daga x2", "Arco Corto", "Armatura di Cuoio (CA 11)", "Arnesi da Scasso"],
    "Ranger": ["Armatura di Cuoio", "Spada Corta x2", "Arco Lungo"],
    "Chierico": ["Mazza", "Scudo", "Simbolo Sacro", "Cotta di Maglia"]
}

XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}

# --- 3. INIZIALIZZAZIONE STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "temp_stats": {}, "ca": 10, "event_log": []
    })

# --- LOGICA LEVEL UP AUTOMATICA ---
prossimo_liv = XP_LEVELS.get(st.session_state.livello + 1, 999999)
if st.session_state.xp >= prossimo_liv:
    st.session_state.livello += 1
    mod_cos = calcola_mod(st.session_state.personaggio['stats']['Costituzione'])
    incremento_hp = (random.randint(1, 10) if st.session_state.personaggio['classe'] == "Guerriero" else 6) + mod_cos
    st.session_state.hp_max += max(1, incremento_hp)
    st.session_state.hp = st.session_state.hp_max
    if st.session_state.spell_slots_max > 0: st.session_state.spell_slots_max += 1
    st.toast(f"✨ LIVELLO AUMENTATO! Mulli è ora di Livello {st.session_state.livello}!", icon="⚔️")

# --- 4. SIDEBAR (CON BARRA XP) ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        
        # Barra XP
        progresso_xp = min(1.0, st.session_state.xp / prossimo_liv)
        st.write(f"✨ XP: {st.session_state.xp} / {prossimo_liv}")
        st.progress(progresso_xp)
        
        c1, c2 = st.columns(2)
        c1.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        c2.metric("🛡️ CA", st.session_state.ca)
        
        with st.expander("📊 Statistiche"):
            for s, v in p['stats'].items():
                st.write(f"**{s}**: {v} ({calcola_mod(v):+})")
        
        with st.expander("✅ Abilità"):
            for skill in p['competenze']:
                bonus = calcola_mod(p['stats'][SKILL_MAP[skill]]) + st.session_state.bonus_competenza
                st.write(f"{skill}: **{bonus:+}**")

        st.divider()
        st.subheader("📖 Guida Difficoltà (CD)")
        st.caption("Facile: 10 | Media: 15 | Difficile: 20")
        
        st.divider()
        save_data = json.dumps({k: v for k, v in st.session_state.items() if k != "GEMINI_API_KEY"}, indent=2)
        st.download_button("💾 Salva", save_data, file_name=f"{p['nome']}_save.json")
        if st.button("🗑️ Reset"):
            st.session_state.clear()
            st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Officina di Mulli")
    # (Logica creazione identica a prima, preservata)
    if not st.session_state.temp_stats:
        if st.button("🎲 Tira Statistiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        cols = st.columns(6)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()): cols[i].metric(s, v)
        with st.form("crea"):
            nome = st.text_input("Nome")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger"])
            if st.form_submit_button("Inizia"):
                if nome:
                    st.session_state.update({
                        "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[classe]},
                        "game_phase": "playing", "hp": 20, "hp_max": 20, "ca": 14, "inventario": EQUIP_AVANZATO[classe]
                    })
                    st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                    st.rerun()
else:
    st.title("🛡️ Avventura")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
    if c2.button("⚔️ Attacco"): st.session_state.ultimo_tiro = random.randint(1, 20) + 5
    if c3.button("⛺ Riposo"): 
        st.session_state.hp = st.session_state.hp_max
        st.success("HP Ripristinati!")
    if c4.button("🔍 Percezione"): 
        mod_sag = calcola_mod(st.session_state.personaggio['stats']['Saggezza'])
        st.session_state.ultimo_tiro = random.randint(1, 20) + mod_sag + st.session_state.bonus_competenza

    if st.session_state.ultimo_tiro: st.info(f"Risultato: **{st.session_state.ultimo_tiro}**")

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "image_url" in msg: st.image(msg["image_url"])

    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        q = f"Sei il DM. Narra l'inizio per {st.session_state.personaggio['nome']}. Bosco, fuoco, notte. Solo narrazione, niente parentesi. Tag: [[LUOGO:Bosco notturno]]."
        res = model.generate_content(q).text
        clean = re.sub(r'\(.*?\)|\[\[.*?\]\]|DM:', '', res).strip()
        st.session_state.messages[-1] = {"role": "assistant", "content": clean, "image_url": genera_img("Campfire forest", "Ambiente")}
        st.rerun()

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        sys = f"DM 5e. PG: {st.session_state.personaggio}. Tiro: {st.session_state.ultimo_tiro}. Tag: [[LUOGO:desc]], [[DANNO:n]], [[ORO:n]], [[XP:n]]."
        res = model.generate_content(sys + "\n" + prompt).text
        
        # Parsing XP e Meccaniche
        xp_m = re.search(r'\[\[XP:(\d+)\]\]', res)
        if xp_m: st.session_state.xp += int(xp_m.group(1))
        d_m = re.search(r'\[\[DANNO:(\d+)\]\]', res)
        if d_m: st.session_state.hp -= int(d_m.group(1))
        
        clean = re.sub(r'\(.*?\)|\[\[.*?\]\]|DM:', '', res).strip()
        img = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Scena") if "[[LUOGO:" in res else None
        st.session_state.messages.append({"role": "assistant", "content": clean, "image_url": img})
        st.session_state.ultimo_tiro = None
        st.rerun()
                    
