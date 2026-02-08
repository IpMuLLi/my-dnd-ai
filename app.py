import streamlit as st
import google.generativeai as genai
import random

# --- CONFIGURAZIONE CORE 2026 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- INIZIALIZZAZIONE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "game_phase" not in st.session_state: st.session_state.game_phase = "creazione"
# Meccaniche Mostro Attuale
if "mostro_attuale" not in st.session_state:
    st.session_state.mostro_attuale = {"nome": None, "hp": 0, "hp_max": 0, "status": []}

# --- FUNZIONI ---
def registra_mostro(nome, hp):
    st.session_state.mostro_attuale = {
        "nome": nome,
        "hp": hp,
        "hp_max": hp,
        "status": []
    }

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.game_phase != "creazione":
        st.metric("Tuo HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        
        # INTERFACCIA COMBATTIMENTO (Appare solo se c'è un mostro)
        if st.session_state.mostro_attuale["nome"]:
            st.divider()
            st.error(f"💢 IN COMBATTIMENTO: {st.session_state.mostro_attuale['nome']}")
            hp_mostro = st.session_state.mostro_attuale['hp']
            hp_max_m = st.session_state.mostro_attuale['hp_max']
            st.progress(max(0.0, hp_mostro / hp_max_m))
            st.caption(f"HP Mostro: {hp_mostro} / {hp_max_m}")
            if st.session_state.mostro_attuale["status"]:
                st.warning(f"Effetti: {', '.join(st.session_state.mostro_attuale['status'])}")
        
        st.divider()
        if st.button("🎲 Tira d20", use_container_width=True):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Hai ottenuto un {st.session_state.ultimo_tiro}!")

# --- LOGICA DI GIOCO ---
st.title("⚔️ D&D Tactical Engine")

if st.session_state.game_phase == "creazione":
    # ... (Form creazione precedente) ...
    with st.form("char_form"):
        nome = st.text_input("Nome Eroe")
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Chierico", "Ranger"])
        if st.form_submit_button("Inizia") and nome:
            st.session_state.personaggio = {"nome": nome, "classe": classe}
            st.session_state.game_phase = "playing"
            st.rerun()
else:
    # Display Scenario e Chat
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"])

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Descrivi la tua azione (es: Attacco il braccio destro)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # System Prompt Tattico
        sys_prompt = f"""
        SEI IL DM. Mostro Attuale: {st.session_state.mostro_attuale}.
        Tiro Dado Giocatore: {st.session_state.get('ultimo_tiro', 'N/A')}.
        
        REGOLE TATTICHE:
        1. Se il giocatore descrive un attacco mirato (es. al braccio), valuta l'effetto narrativo.
        2. Se appare un mostro usa: [[NUOVO_MOSTRO:Nome:HP]]
        3. Se il mostro subisce danni: [[DANNO_MOSTRO:X]]
        4. Se l'attacco causa un malus (es. braccio rotto): [[STATUS_MOSTRO:descrizione breve]]
        5. Se il mostro muore (HP=0), descrivi la sua fine e usa [[MORTE_MOSTRO]].
        """
        
        with st.chat_message("assistant"):
            response = model.generate_content(sys_prompt + "\n" + prompt).text
            
            # PARSING TATTICO
            if "[[NUOVO_MOSTRO:" in response:
                dati = response.split("[[NUOVO_MOSTRO:")[1].split("]]")[0].split(":")
                registra_mostro(dati[0], int(dati[1]))
            
            if "[[DANNO_MOSTRO:" in response:
                danno = int(response.split("[[DANNO_MOSTRO:")[1].split("]]")[0])
                st.session_state.mostro_attuale["hp"] -= danno
            
            if "[[STATUS_MOSTRO:" in response:
                effetto = response.split("[[STATUS_MOSTRO:")[1].split("]]")[0]
                st.session_state.mostro_attuale["status"].append(effetto)
            
            if "[[MORTE_MOSTRO]]" in response:
                st.session_state.mostro_attuale = {"nome": None, "hp": 0, "hp_max": 0, "status": []}

            # ... (Altro parsing DANNO/ORO/XP...)

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
