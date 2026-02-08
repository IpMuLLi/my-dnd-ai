import streamlit as st
import google.generativeai as genai
import random
import json

# --- CONFIGURAZIONE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. INIZIALIZZAZIONE ---
def tira_statistica():
    # Tira 4d6 e scarta il più basso
    dadi = [random.randint(1, 6) for _ in range(4)]
    return sum(sorted(dadi)[1:])

def init_state():
    defaults = {
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}},
        "hp": 20, "hp_max": 20, "oro": 0, "xp": 0, "livello": 1,
        "inventario": [], "mostro_attuale": {"nome": None, "hp": 0, "hp_max": 0, "status": []},
        "current_image": None, "gallery": [], "bestiario": {},
        "diario": "L'avventura ha inizio...",
        "spell_slots_max": 0, "spell_slots_curr": 0, "ultimo_tiro": None,
        "immersiva": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# --- 2. DATI CLASSI ---
DATA_CLASSI = {
    "Guerriero": {"hp": 12, "slots": 0, "equip": ["Spada Lunga", "Scudo", "Cotta di Maglia"]},
    "Mago": {"hp": 6, "slots": 3, "equip": ["Bastone Arcano", "Libro Incantesimi"]},
    "Ladro": {"hp": 8, "slots": 0, "equip": ["2 Pugnali", "Attrezzi da Scasso", "Arco Corto"]},
    "Chierico": {"hp": 8, "slots": 3, "equip": ["Mazza", "Simbolo Sacro", "Armatura di Scaglie"]},
    "Ranger": {"hp": 10, "slots": 2, "equip": ["Arco Lungo", "20 Frecce", "2 Spade Corte"]}
}

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    st.session_state.immersiva = st.toggle("🌌 Modalità Immersiva", value=st.session_state.immersiva)
    
    if st.session_state.game_phase != "creazione" and not st.session_state.immersiva:
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        
        # Caratteristiche
        with st.expander("📊 Punti Caratteristica", expanded=True):
            cols = st.columns(3)
            s = st.session_state.personaggio['stats']
            cols[0].metric("FOR", s['Forza'])
            cols[1].metric("DES", s['Destrezza'])
            cols[2].metric("COS", s['Costituzione'])
            cols[0].metric("INT", s['Intelligenza'])
            cols[1].metric("SAG", s['Saggezza'])
            cols[2].metric("CAR", s['Carisma'])

        st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))
        
        with st.expander("🎒 Zaino & Magie"):
            st.write("**Oro:** " + str(st.session_state.oro) + "g")
            st.write("**Inventario:** " + ", ".join(st.session_state.inventario))
            if st.session_state.spell_slots_max > 0:
                st.write(f"**Slot Magia:** {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")

        if st.button("🎲 Tira d20", use_container_width=True):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Risultato: {st.session_state.ultimo_tiro}")

    if st.button("🗑️ Reset Totale"):
        st.session_state.clear()
        st.rerun()

# --- 4. LOGICA DI GIOCO ---
st.title("⚔️ D&D Engine: Story Starter")

if st.session_state.game_phase == "creazione":
    
    with st.form("creazione_form"):
        nome = st.text_input("Nome dell'Eroe")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
        classe = st.selectbox("Classe", list(DATA_CLASSI.keys()))
        if st.form_submit_button("Inizia l'Avventura") and nome:
            c_data = DATA_CLASSI[classe]
            st.session_state.personaggio = {
                "nome": nome, "classe": classe, "razza": razza,
                "stats": {
                    "Forza": tira_statistica(), "Destrezza": tira_statistica(),
                    "Costituzione": tira_statistica(), "Intelligenza": tira_statistica(),
                    "Saggezza": tira_statistica(), "Carisma": tira_statistica()
                }
            }
            st.session_state.hp_max = c_data["hp"] + (st.session_state.personaggio["stats"]["Costituzione"] // 2 - 5)
            st.session_state.hp = st.session_state.hp_max
            st.session_state.inventario = ["Razioni", "Otre"] + c_data["equip"]
            st.session_state.spell_slots_max = c_data["slots"]
            st.session_state.spell_slots_curr = c_data["slots"]
            st.session_state.oro = random.randint(10, 100)
            st.session_state.game_phase = "playing"
            
            # --- INCIPIT AUTOMATICO ---
            incipit_prompt = f"Sei il DM. Il giocatore è un {razza} {classe} di nome {nome}. Inizia l'avventura descrivendo una scena iniziale drammatica e coinvolgente in un luogo iconico. Usa il tag [[LUOGO:descrizione]] per generare l'immagine."
            response = model.generate_content(incipit_prompt).text
            if "[[LUOGO:" in response:
                loc = response.split("[[LUOGO:")[1].split("]]")[0]
                url = f"https://pollinations.ai/p/{loc.replace(' ', '_')}?width=1024&height=1024&nologo=true"
                st.session_state.current_image = {"url": url, "caption": f"Luogo: {loc[:30]}"}
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

else:
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"])

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_prompt = f"DM. Eroe: {st.session_state.personaggio}. HP: {st.session_state.hp}. Dado: {st.session_state.ultimo_tiro}. Usa i tag meccanici [[DANNO]], [[XP]], [[LUOGO]], ecc."
        
        with st.chat_message("assistant"):
            response = model.generate_content(sys_prompt + "\n" + prompt).text
            # ... (Parsing dei tag come negli script precedenti) ...
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
