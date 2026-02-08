import streamlit as st
import google.generativeai as genai
import random
import re

# --- CONFIGURAZIONE GEMINI ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- INIZIALIZZAZIONE MEMORIA ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "hp" not in st.session_state:
    st.session_state.hp = 20
if "inventario" not in st.session_state:
    st.session_state.inventario = ["Spada corta", "Razioni", "Corda"]
if "ultimo_tiro" not in st.session_state:
    st.session_state.ultimo_tiro = None

# --- FUNZIONE PER GESTIRE I DANNI AUTOMATICI ---
def controlla_danni(testo_ai):
    # Cerca nel testo frasi come "perdi 5 HP" o "subisci 3 danni"
    numeri = re.findall(r'(\d+)\s*(?:danni|HP|punti vita)', testo_ai.lower())
    if numeri:
        danno = int(numeri[0])
        st.session_state.hp -= danno
        return danno
    return 0

# --- INTERFACCIA LATERALE (SIDEBAR) ---
with st.sidebar:
    st.title("🛡️ Scheda Personaggio")
    st.metric(label="Punti Vita (HP)", value=st.session_state.hp)
    
    st.write("**Inventario:**")
    for oggetto in st.session_state.inventario:
        st.write(f"- {oggetto}")
    
    st.divider()
    
    if st.button("🎲 Lancia d20"):
        st.session_state.ultimo_tiro = random.randint(1, 20)
        st.info(f"Hai lanciato un {st.session_state.ultimo_tiro}!")

    st.divider()
    
    # TASTO PER SALVARE (MEMORIA STORICA)
    st.subheader("Memoria Storica")
    storia_completa = ""
    for m in st.session_state.messages:
        storia_completa += f"{m['role'].upper()}: {m['content']}\n\n"
    
    st.download_button(
        label="💾 Scarica Avventura",
        data=storia_completa,
        file_name="avventura_dnd.txt",
        mime="text/plain"
    )

# --- INTERFACCIA CHAT ---
st.title("🐉 D&D Master AI")

# Visualizza i messaggi precedenti
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input dell'utente
if prompt := st.chat_input("Cosa fai?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # ISTRUZIONI DI SISTEMA (IL DM GUIDA IL GIOCO)
        system_instruction = f"""
        Sei un Dungeon Master di D&D 5e esperto e narrativo.
        Punti Vita Giocatore: {st.session_state.hp}.
        Inventario: {st.session_state.inventario}.
        Ultimo dado lanciato: {st.session_state.ultimo_tiro}.
        
        REGOLE IMPORTANTI:
        1. Se il giocatore subisce danni, scrivi esplicitamente 'perdi X HP' (es. 'L'orco ti colpisce, perdi 4 HP').
        2. Guida tu l'avventura: non aspettare che il giocatore faccia tutto, descrivi l'ambiente e proponi 2 o 3 scelte possibili alla fine di ogni messaggio.
        3. Sii descrittivo e mantieni il tono fantasy.
        """
        
        # Generazione risposta
        response = model.generate_content(system_instruction + "\n" + prompt)
        testo_risposta = response.text
        
        # Controllo danni automatico
        danno_subito = controlla_danni(testo_risposta)
        if danno_subito > 0:
            st.warning(f"⚠️ Attenzione! Hai perso {danno_subito} HP!")
            
        st.markdown(testo_risposta)
        st.session_state.messages.append({"role": "assistant", "content": testo_risposta})
        
        # Reset del dado dopo che è stato usato
        st.session_state.ultimo_tiro = None
        
