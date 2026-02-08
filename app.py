import streamlit as st
import google.generativeai as genai
import random

# --- CONFIGURAZIONE CORE 2026 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- FUNZIONE PER CARICARE LA STORIA ---
def carica_storia(file_caricato):
    if file_caricato is not None:
        stringio = file_caricato.getvalue().decode("utf-8")
        linee = stringio.split("\n\n")
        nuovi_messaggi = []
        for linea in linee:
            if ":" in linea:
                ruolo, contenuto = linea.split(":", 1)
                nuovi_messaggi.append({"role": ruolo.lower().strip(), "content": contenuto.strip()})
        st.session_state.messages = nuovi_messaggi
        st.success("Avventura caricata con successo!")

# --- INIZIALIZZAZIONE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "hp" not in st.session_state:
    st.session_state.hp = 20
if "inventario" not in st.session_state:
    st.session_state.inventario = ["Spada lunga", "Pozione di cura"]

# --- SIDEBAR 2026 ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    st.metric("Punti Vita", f"{st.session_state.hp} / 20")
    st.progress(max(0, st.session_state.hp / 20))
    
    st.subheader("🎒 Zaino")
    st.write(", ".join(st.session_state.inventario))
    
    if st.button("🎲 Tira d20", use_container_width=True):
        st.session_state.ultimo_tiro = random.randint(1, 20)
        st.toast(f"Hai ottenuto un {st.session_state.ultimo_tiro}!")

    st.divider()
    
    # GESTIONE SALVATAGGI (MEMORIA)
    st.subheader("💾 Memoria Storica")
    
    # Tasto Scarica
    full_history = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
    st.download_button("Scarica Salvataggio", full_history, file_name="salvataggio_dnd.txt")
    
    # Caricamento File
    file_da_caricare = st.file_uploader("Carica un'avventura", type=["txt"])
    if st.button("Conferma Caricamento"):
        carica_storia(file_da_caricare)

# --- LOGICA CHAT ---
st.title("🧙‍♂️ DM Gemini 2.5 Flash Lite")

if not st.session_state.messages:
    intro = model.generate_content("Sei un DM. Inizia l'avventura e chiedimi chi sono.")
    st.session_state.messages.append({"role": "assistant", "content": intro.text})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Cosa fai?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompt = f"HP: {st.session_state.hp}, DADO: {st.session_state.get('ultimo_tiro', 'N/A')}. Se subisco danni scrivi [[DANNO:X]]."
    
    with st.chat_message("assistant"):
        response = model.generate_content(system_prompt + "\n" + prompt)
        output = response.text
        
        if "[[DANNO:" in output:
            try:
                danno = int(output.split("[[DANNO:")[1].split("]]")[0])
                st.session_state.hp -= danno
            except: pass

        st.markdown(output)
        st.session_state.messages.append({"role": "assistant", "content": output})
        st.session_state.ultimo_tiro = None
        
