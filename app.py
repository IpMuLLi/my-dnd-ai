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
        prompt_base = f"Dungeons and Dragons high fantasy, {tipo}: {descrizione}, volumetric lighting, 8k, masterpiece"
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

# --- 3. INIZIALIZZAZIONE ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "temp_stats": {}, "ca": 10, "event_log": []
    })

# --- 4. SIDEBAR (SCHEDA DEFINITIVA) ---
with st.sidebar:
    st.title("🧝 Scheda Personaggio")
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        st.subheader(f"{p['nome']} - {p['razza']} {p['classe']}")
        
        col1, col2 = st.columns(2)
        col1.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        col2.metric("🛡️ CA", st.session_state.ca)
        
        col3, col4 = st.columns(2)
        col3.metric("🪙 Oro", st.session_state.oro)
        col4.metric("✨ Liv", st.session_state.livello)

        with st.expander("📊 Caratteristiche"):
            for s, v in p['stats'].items():
                st.write(f"**{s}**: {v} ({calcola_mod(v):+})")
        
        with st.expander("✅ Abilità"):
            for skill in p['competenze']:
                bonus = calcola_mod(p['stats'][SKILL_MAP[skill]]) + st.session_state.bonus_competenza
                st.write(f"{skill}: **{bonus:+}**")

        with st.expander("🎒 Inventario"):
            for item in st.session_state.inventario: st.write(f"- {item}")

        if st.session_state.event_log:
            with st.expander("📝 Diario Eventi"):
                for e in st.session_state.event_log[-5:]: st.write(e)

        st.divider()
        save_data = json.dumps({k: v for k, v in st.session_state.items() if k != "GEMINI_API_KEY"}, indent=2)
        st.download_button("💾 Salva JSON", save_data, file_name=f"{p['nome']}_save.json")
        if st.button("🗑️ Reset"):
            st.session_state.clear()
            st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 D&D Legend Engine - Creazione")
    
    with st.expander("📂 Carica Personaggio"):
        up_file = st.file_uploader("Carica .json", type="json")
        if up_file:
            data = json.load(up_file)
            for k, v in data.items(): st.session_state[k] = v
            st.rerun()

    if not st.session_state.temp_stats:
        if st.button("🎲 Tira Statistiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        st.write("I tuoi tiri:")
        cols = st.columns(6)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i].metric(s, v)
        
        if st.button("🔄 Reroll"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()

        with st.form("crea"):
            nome = st.text_input("Nome Eroe")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Mezzelfo", "Tiefling"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Crea"):
                if nome:
                    mod_cos = calcola_mod(st.session_state.temp_stats["Costituzione"])
                    mod_des = calcola_mod(st.session_state.temp_stats["Destrezza"])
                    hp_max = 10 + mod_cos + (10 if classe=="Guerriero" else 8)
                    ca_base = 10 + mod_des + (6 if classe=="Guerriero" else 2 if classe=="Ladro" else 0)
                    
                    st.session_state.update({
                        "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[classe]},
                        "hp": hp_max, "hp_max": hp_max, "ca": ca_base,
                        "inventario": EQUIP_AVANZATO[classe], "game_phase": "playing",
                        "spell_slots_max": 3 if classe in ["Mago", "Chierico"] else 0,
                        "spell_slots_curr": 3 if classe in ["Mago", "Chierico"] else 0
                    })
                    st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                    st.rerun()

else:
    st.title("🛡️ Avventura in Corso")
    
    # Pulsantiera
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
    if c2.button("⚔️ Attacco"): 
        mod = calcola_mod(st.session_state.personaggio['stats']['Forza'])
        st.session_state.ultimo_tiro = random.randint(1, 20) + mod + st.session_state.bonus_competenza
    if c3.button("⛺ Riposo"):
        st.session_state.hp = st.session_state.hp_max
        st.session_state.spell_slots_curr = st.session_state.spell_slots_max
        st.success("Riposato!")
    if c4.button("✨ Magia"):
        if st.session_state.spell_slots_curr > 0:
            st.session_state.spell_slots_curr -= 1
            st.session_state.ultimo_tiro = random.randint(1, 20) + 5
        else: st.error("Slot esauriti!")

    if st.session_state.ultimo_tiro: st.info(f"Ultimo Tiro: **{st.session_state.ultimo_tiro}**")

    # Chat
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "image_url" in msg: st.image(msg["image_url"])

    # Intro
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        with st.chat_message("assistant"):
            q = f"DM 5e. Introduci {st.session_state.personaggio['nome']} nel Bosco di notte al fuoco. Usa [[LUOGO:Bosco notturno fuoco]]."
            res = model.generate_content(q).text
            img = genera_img("Campfire in dark forest, D&D", "Ambiente")
            clean = re.sub(r'\[\[.*?\]\]', '', res).strip()
            if clean.endswith((" della", " del")): clean += " radura."
            st.write(clean)
            if img: st.image(img)
            st.session_state.messages[-1] = {"role": "assistant", "content": clean, "image_url": img}
            st.rerun()

    # Input
    if prompt := st.chat_input("Cosa vuoi fare?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        sys = f"DM 5e. PG: {st.session_state.personaggio}. Tiro: {st.session_state.ultimo_tiro}. Usa [[LUOGO:desc]], [[DANNO:n]], [[ORO:n]], [[ITEM:n]]."
        with st.chat_message("assistant"):
            res = model.generate_content(sys + "\n" + prompt).text
            img = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Scena") if "[[LUOGO:" in res else None
            
            # Parsing Meccanico
            d_m = re.search(r'\[\[DANNO:(\d+)\]\]', res)
            if d_m: 
                st.session_state.hp -= int(d_m.group(1))
                st.session_state.event_log.append(f"💥 Subiti {d_m.group(1)} danni")
            o_m = re.search(r'\[\[ORO:(-?\d+)\]\]', res)
            if o_m: st.session_state.oro += int(o_m.group(1))
            
            clean = re.sub(r'\[\[.*?\]\]', '', res).strip()
            st.write(clean)
            if img: st.image(img)
            st.session_state.messages.append({"role": "assistant", "content": clean, "image_url": img})
            st.session_state.ultimo_tiro = None
            st.rerun()
                    
