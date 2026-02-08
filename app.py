import streamlit as st
import google.generativeai as genai
import random

# --- CONFIGURAZIONE GEMINI ---
# Recupera la chiave API dai "Secrets" di Replit
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- INIZIALIZZAZIONE MEMORIA ---
# Streamlit usa 'session_state' per ricordare le cose mentre l'app è aperta
if "messages" not in st.session_state:
    st.session_state.messages = [] # Storia della chat
if "hp" not in st.session_state:
    st.session_state.hp = 20 # Vita del personaggio
if "inventario" not in st.session_state:
    st.session_state.inventario = ["Spada corta", "Razioni", "Corda"]

# --- INTERFACCIA LATERALE (SIDEBAR) ---
with st.sidebar:
    st.title("🛡️ Scheda Personaggio")
    st.metric(label="Punti Vita (HP)", value=st.session_state.hp)
    st.write("**Inventario:**")
    for oggetto in st.session_state.inventario:
        st.write(f"- {oggetto}")
    
    if st.button("🎲 Lancia d20"):
        dado = random.randint(1, 20)
        st.session_state.ultimo_tiro = dado
        st.info(f"Hai lanciato un {dado}!")

# --- INTERFACCIA CHAT ---
st.title("🐉 D&D Master AI")

# Visualizza i messaggi precedenti
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input dell'utente
if prompt := st.chat_input("Cosa vuoi fare?"):
    # Aggiungi il messaggio dell'utente alla memoria
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Chiedi a Gemini di rispondere come DM
    with st.chat_message("assistant"):
        # Creiamo un "super prompt" che include le stats e il tiro di dado
        context = f"""Tu sei un Dungeon Master esperto. 
        Il giocatore ha {st.session_state.hp} HP. 
        Inventario: {st.session_state.inventario}.
        Ultimo tiro di dado: {st.get('ultimo_tiro', 'Nessuno')}.
        Rispondi in modo immersivo e breve."""
        
        # Uniamo il contesto alla storia della chat
        full_prompt = context + "\n" + prompt
        response = model.generate_content(full_prompt)
        
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
