import streamlit as st
import google.generativeai as genai
import random

# --- CONFIGURAZIONE CORE 2026 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- INIZIALIZZAZIONE STATO ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "game_phase" not in st.session_state:
    st.session_state.game_phase = "creazione"
if "personaggio" not in st.session_state:
    st.session_state.personaggio = {"nome": "", "classe": "", "razza": "", "abilita": []}
if "hp_max" not in st.session_state:
    st.session_state.hp_max = 20
if "hp" not in st.session_state:
    st.session_state.hp = 20
if "livello" not in st.session_state:
    st.session_state.livello = 1
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "oro" not in st.session_state:
    st.session_state.oro = 50
if "inventario" not in st.session_state:
    st.session_state.inventario = ["Razioni", "Acciarino"]

# --- DIZIONARIO ABILITÀ ---
ABILITA_CLASSI = {
    "Guerriero": ["Secondo Vento", "Stile di Combattimento"],
    "Mago": ["Recupero Arcano", "Incantesimi di Livello 1"],
    "Ladro": ["Attacco Furtivo", "Esperto di Serrature"],
    "Chierico": ["Incanalare Divinità", "Cura Ferite"],
    "Ranger": ["Nemico Prescelto", "Esploratore Naturale", "Tiro Preciso"]
}

# --- FUNZIONI ---
def controlla_livello():
    soglia = st.session_state.livello * 100
    if st.session_state.xp >= soglia:
        st.session_state.livello += 1
        st.session_state.xp -= soglia
        st.session_state.hp_max += 10
        st.session_state.hp = st.session_state.hp_max
        st.toast(f"✨ LEVEL UP! Livello {st.session_state.livello}!", icon="⚔️")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.game_phase != "creazione":
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        st.caption(f"{st.session_state.personaggio['razza']} {st.session_state.personaggio['classe']}")
        
        # HP e XP
        st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))
        st.write(f"XP: {st.session_state.xp} / {st.session_state.livello * 100}")
        st.progress(st.session_state.xp / (st.session_state.livello * 100))
        
        # SEZIONE ABILITÀ SPECIALI
        st.divider()
        st.subheader("✨ Abilità Speciali")
        for abi in st.session_state.personaggio["abilita"]:
            st.info(abi)
        
        st.divider()
        st.metric("💰 Oro", f"{st.session_state.oro} gp")
        st.subheader("🎒 Zaino")
        st.write(", ".join(st.session_state.inventario))
        
        if st.button("🎲 Tira d20", use_container_width=True):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Hai ottenuto un {st.session_state.ultimo_tiro}!")

    if st.button("🗑️ Reset Totale"):
        st.session_state.clear()
        st.rerun()

# --- LOGICA DI GIOCO ---
st.title("🧙‍♂️ D&D Engine 2026")

if st.session_state.game_phase == "creazione":
    st.subheader("Creazione dell'Eroe")
    with st.form("char_form"):
        nome = st.text_input("Nome")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
        classe = st.selectbox("Classe", list(ABILITA_CLASSI.keys()))
        if st.form_submit_button("Inizia l'Avventura") and nome:
            st.session_state.personaggio = {
                "nome": nome, 
                "razza": razza, 
                "classe": classe,
                "abilita": ABILITA_CLASSI[classe]
            }
            st.session_state.game_phase = "playing"
            st.rerun()

else:
    if not st.session_state.messages:
        p = st.session_state.personaggio
        intro = model.generate_content(f"Sei il DM. Inizia l'avventura per {p['nome']}, {p['razza']} {p['classe']}. Usa le sue abilità: {p['abilita']}.")
        st.session_state.messages.append({"role": "assistant", "content": intro.text})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        sys_prompt = f"GIOCO: {st.session_state.personaggio} | HP: {st.session_state.hp} | DADO: {st.session_state.get('ultimo_tiro', 'N/A')}"
        
        with st.chat_message("assistant"):
            response = model.generate_content(sys_prompt + "\n" + prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.session_state.ultimo_tiro = None
            st.rerun()
