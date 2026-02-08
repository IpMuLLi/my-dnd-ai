import streamlit as st
import google.generativeai as genai
import random

# --- CONFIGURAZIONE CORE 2026 ---
# Assicurati di avere la chiave API nei Secrets di Streamlit
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. INIZIALIZZAZIONE SICURA (FIX PER ATTRIBUTEERROR) ---
def init_state():
    defaults = {
        "messages": [],
        "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "abilita": [], "incantesimi": []},
        "hp": 20,
        "hp_max": 20,
        "oro": 50,
        "xp": 0,
        "livello": 1,
        "inventario": ["Razioni", "Acciarino"],
        "mostro_attuale": {"nome": None, "hp": 0, "hp_max": 0, "status": []},
        "current_image": None,
        "gallery": [],
        "bestiario": {},
        "diario": "L'avventura ha inizio...",
        "spell_slots_max": 0,
        "spell_slots_curr": 0,
        "ultimo_tiro": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# --- 2. DATI DI GIOCO ---
ABILITA_DATA = {
    "Guerriero": {"abi": ["Secondo Vento", "Azione Impetuosa"], "spells": [], "slots": 0},
    "Mago": {"abi": ["Recupero Arcano"], "spells": ["Dardo Incantato", "Scudo", "Mani Brucianti"], "slots": 3},
    "Ladro": {"abi": ["Attacco Furtivo", "Mani di Fata"], "spells": [], "slots": 0},
    "Chierico": {"abi": ["Luce Sacra"], "spells": ["Cura Ferite", "Dardo Guida"], "slots": 3},
    "Ranger": {"abi": ["Tiro Preciso"], "spells": ["Marchio del Cacciatore"], "slots": 2}
}

# --- 3. FUNZIONI CORE ---
def registra_evento_visivo(descrizione, tipo):
    url = f"https://pollinations.ai/p/{descrizione.replace(' ', '_')}?width=1024&height=1024&nologo=true"
    nuova_img = {"url": url, "caption": f"{tipo}: {descrizione[:30]}..."}
    st.session_state.current_image = nuova_img
    st.session_state.gallery.append(nuova_img)
    return url

def controlla_livello():
    soglia = st.session_state.livello * 100
    if st.session_state.xp >= soglia:
        st.session_state.livello += 1
        st.session_state.hp_max += 10
        st.session_state.hp = st.session_state.hp_max
        st.toast(f"✨ LEVEL UP! Sei al livello {st.session_state.livello}!", icon="⚔️")

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    
    if st.session_state.game_phase != "creazione":
        # Statistiche Eroe
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))
        
        col1, col2 = st.columns(2)
        col1.metric("💰 Oro", f"{st.session_state.oro}g")
        col2.metric("🔮 Slot", f"{st.session_state.spell_slots_curr}")

        # Combattimento Attivo
        if st.session_state.mostro_attuale["nome"]:
            st.divider()
            st.error(f"💢 NEMICO: {st.session_state.mostro_attuale['nome']}")
            hp_m = st.session_state.mostro_attuale['hp']
            hp_max_m = st.session_state.mostro_attuale['hp_max']
            st.progress(max(0.0, hp_m / hp_max_m) if hp_max_m > 0 else 0)
            if st.session_state.mostro_attuale["status"]:
                st.caption(f"Status: {', '.join(st.session_state.mostro_attuale['status'])}")

        # Expander Utilità
        with st.expander("📖 Diario & Bestiario"):
            st.write("**Ultimi Eventi:**")
            st.caption(st.session_state.diario)
            st.divider()
            st.write("**Creature Note:**")
            st.write(", ".join(st.session_state.bestiario.keys()) if st.session_state.bestiario else "Nessuna")

        if st.button("🎲 Tira d20", use_container_width=True):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Risultato: {st.session_state.ultimo_tiro}")

    if st.button("🗑️ Reset Totale"):
        st.session_state.clear()
        st.rerun()

# --- 5. LOGICA DI GIOCO ---
st.title("⚔️ D&D Engine 2026: Tactical Edition")

if st.session_state.game_phase == "creazione":
    st.subheader("Crea il tuo Destino")
    with st.form("char_form"):
        nome = st.text_input("Nome dell'Eroe")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
        classe = st.selectbox("Classe", list(ABILITA_DATA.keys()))
        if st.form_submit_button("Inizia Avventura") and nome:
            data = ABILITA_DATA[classe]
            st.session_state.personaggio = {
                "nome": nome, "razza": razza, "classe": classe,
                "abilita": data["abi"], "incantesimi": data["spells"]
            }
            st.session_state.spell_slots_max = data["slots"]
            st.session_state.spell_slots_curr = data["slots"]
            st.session_state.game_phase = "playing"
            st.rerun()

else:
    # Scenario Visuale
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"], caption=st.session_state.current_image["caption"])

    # Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # Input Giocatore
    if prompt := st.chat_input("Cosa fai? (Descrivi la tua mossa tattica)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        sys_prompt = f"""
        SEI IL DM. Giocatore: {st.session_state.personaggio}. HP: {st.session_state.hp}/{st.session_state.hp_max}.
        Mostro: {st.session_state.mostro_attuale}. Dado: {st.session_state.ultimo_tiro}.
        
        REGOLE MECCANICHE (Usa questi tag):
        - Mostri: [[NUOVO_MOSTRO:Nome:HP]] o [[DANNO_MOSTRO:X]] o [[STATUS_MOSTRO:effetto]] o [[MORTE_MOSTRO]]
        - Loot/Luoghi: [[LOOT:descrizione]] o [[LUOGO:descrizione]]
        - Personaggio: [[DANNO:X]], [[CURA:X]], [[ORO:X]], [[XP:X]], [[PRENDI:Oggetto]], [[USA_SLOT:1]]
        - Diario: [[DIARIO:riassunto breve degli ultimi eventi]]
        """
        
        with st.chat_message("assistant"):
            response = model.generate_content(sys_prompt + "\n" + prompt).text
            
            # --- PARSING AVANZATO ---
            if "[[NUOVO_MOSTRO:" in response:
                d = response.split("[[NUOVO_MOSTRO:")[1].split("]]")[0].split(":")
                st.session_state.mostro_attuale = {"nome": d[0], "hp": int(d[1]), "hp_max": int(d[1]), "status": []}
                url = registra_evento_visivo(d[0], "Mostro")
                st.session_state.bestiario[d[0]] = {"img": url, "desc": "Incontrato"}

            if "[[DANNO_MOSTRO:" in response:
                val = int(response.split("[[DANNO_MOSTRO:")[1].split("]]")[0])
                st.session_state.mostro_attuale["hp"] -= val

            if "[[STATUS_MOSTRO:" in response:
                eff = response.split("[[STATUS_MOSTRO:")[1].split("]]")[0]
                st.session_state.mostro_attuale["status"].append(eff)

            if "[[MORTE_MOSTRO]]" in response:
                st.session_state.mostro_attuale = {"nome": None, "hp": 0, "hp_max": 0, "status": []}

            if "[[LUOGO:" in response: registra_evento_visivo(response.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            if "[[LOOT:" in response: registra_evento_visivo(response.split("[[LOOT:")[1].split("]]")[0], "Loot")
            if "[[DIARIO:" in response: st.session_state.diario = response.split("[[DIARIO:")[1].split("]]")[0]
            
            # Statistiche Eroe
            if "[[DANNO:" in response: st.session_state.hp -= int(response.split("[[DANNO:")[1].split("]]")[0])
            if "[[CURA:" in response: st.session_state.hp = min(st.session_state.hp_max, st.session_state.hp + int(response.split("[[CURA:")[1].split("]]")[0]))
            if "[[ORO:" in response: st.session_state.oro += int(response.split("[[ORO:")[1].split("]]")[0])
            if "[[XP:" in response: st.session_state.xp += int(response.split("[[XP:")[1].split("]]")[0])
            if "[[PRENDI:" in response: st.session_state.inventario.append(response.split("[[PRENDI:")[1].split("]]")[0])
            if "[[USA_SLOT:" in response: st.session_state.spell_slots_curr = max(0, st.session_state.spell_slots_curr - int(response.split("[[USA_SLOT:")[1].split("]]")[0]))

            controlla_livello()
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.ultimo_tiro = None # Reset dado
            st.rerun()
            
