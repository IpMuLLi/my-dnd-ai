import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="centered", initial_sidebar_state="collapsed")

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
        prompt_base = f"Dungeons and Dragons high fantasy scene, {tipo}: {descrizione}, volumetric lighting, 8k, masterpiece"
        prompt_encoded = urllib.parse.quote(prompt_base)
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
        return url
    except: return None

# --- 2. LOGICA D&D (PRESERVATA) ---
DADI_VITA = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}
COMPETENZE_CLASSE = {
    "Guerriero": ["Atletica", "Percezione"], "Mago": ["Arcano", "Storia"],
    "Ladro": ["Furtività", "Rapidità di mano", "Indagare"], "Ranger": ["Sopravvivenza", "Percezione"],
    "Chierico": ["Religione", "Intuizione"]
}
EQUIPAGGIAMENTO_STANDARD = {
    "Guerriero": ["Cotta di Maglia", "Spada Lunga", "Scudo"], "Mago": ["Bastone Arcano", "Libro Incantesimi"],
    "Ladro": ["Daghe", "Arnesi da scasso"], "Ranger": ["Arco Lungo", "Armatura Cuoio"],
    "Chierico": ["Mazza", "Simbolo Sacro"]
}

# --- 3. INIZIALIZZAZIONE ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "current_image": None, "gallery": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "temp_stats": {}, "diario": ""
    })

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        st.metric("Punti Vita ❤️", f"{st.session_state.hp}/{st.session_state.hp_max}")
        st.metric("Oro 🪙", f"{st.session_state.oro}gp")
        with st.expander("📊 Statistiche"):
            for s, v in st.session_state.personaggio['stats'].items():
                st.write(f"**{s}**: {v} ({calcola_mod(v):+})")
        if st.button("🗑️ Reset"):
            st.session_state.clear()
            st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Creazione Personaggio")
    
    with st.expander("📂 Carica Salvataggio"):
        up_file = st.file_uploader("Trascina qui il file .json", type="json")
        if up_file:
            data = json.load(up_file)
            for k, v in data.items(): st.session_state[k] = v
            st.rerun()

    if not st.session_state.temp_stats:
        if st.button("🎲 Tira i Dadi"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        cols = st.columns(3)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i%3].metric(s, v)
        
        if st.button("🔄 Reroll"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()

        with st.form("finale"):
            nome = st.text_input("Nome")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia") and nome:
                hp_tot = DADI_VITA[classe] + calcola_mod(st.session_state.temp_stats["Costituzione"])
                st.session_state.update({
                    "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[classe]},
                    "hp": hp_tot, "hp_max": hp_tot, "inventario": EQUIPAGGIAMENTO_STANDARD[classe], "game_phase": "playing"
                })
                # Il trucco: Messaggio di sistema pulito per l'intro
                st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                st.rerun()

else:
    st.title("⚔️ D&D Legend Engine")
    
    # Area Azioni Rapide
    c1, c2, c3 = st.columns(3)
    if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
    if c2.button("⛺ Riposo"): 
        st.session_state.hp = st.session_state.hp_max
        st.success("Riposato!")
    if st.session_state.ultimo_tiro: st.info(f"Dado: {st.session_state.ultimo_tiro}")

    # Rendering Messaggi
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "image_url" in msg: st.image(msg["image_url"])

    # Gestore Introduzione (Riparato)
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        with st.spinner("Il DM sta arrivando..."):
            intro_q = f"Sei un DM di D&D. Scrivi un'introduzione epica e COMPLETA per {st.session_state.personaggio['nome']}, un {st.session_state.personaggio['razza']} {st.session_state.personaggio['classe']}. Si trova in un bosco scuro vicino a un fuoco. NON lasciare frasi in sospeso. Concludi SEMPRE con il tag [[LUOGO:Bosco notturno con fuoco da campo]]."
            res = model.generate_content(intro_q).text
            
            # Parsing Immagine
            img_url = None
            if "[[LUOGO:" in res:
                img_url = genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Ambiente")
            
            clean_res = re.sub(r'\[\[.*?\]\]', '', res).strip()
            # Se la frase finisce male (es. con un punto e spazio o preposizione), la chiudiamo forzatamente
            if clean_res.endswith((" della", " del", " lo", " la")): clean_res += " foresta antica."

            st.session_state.messages[-1] = {"role": "assistant", "content": clean_res, "image_url": img_url}
            st.rerun()

    # Chat Input Standard
    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        sys_p = f"DM 5e. PG: {st.session_state.personaggio}. HP: {st.session_state.hp}. Tiro: {st.session_state.ultimo_tiro}. Usa [[LUOGO:desc]], [[DANNO:n]], [[ORO:n]]. Mai frasi mozze."
        
        with st.chat_message("assistant"):
            full_res = model.generate_content(sys_p + "\n" + prompt).text
            img_url = None
            if "[[LUOGO:" in full_res:
                img_url = genera_img(full_res.split("[[LUOGO:")[1].split("]]")[0], "Scena")
            
            # Logica meccanica
            d_m = re.search(r'\[\[DANNO:(\d+)\]\]', full_res)
            if d_m: st.session_state.hp -= int(d_m.group(1))
            
            clean_res = re.sub(r'\[\[.*?\]\]', '', full_res).strip()
            st.markdown(clean_res)
            if img_url: st.image(img_url)
            
            st.session_state.messages.append({"role": "assistant", "content": clean_res, "image_url": img_url})
            st.session_state.ultimo_tiro = None
            st.rerun()
    
