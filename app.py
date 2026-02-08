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

# --- 1. INIZIALIZZAZIONE ATOMICA ---
def init_state():
    defaults = {
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "abilita": [], "incantesimi": []},
        "hp": 20, "hp_max": 20, "oro": 50, "xp": 0, "livello": 1,
        "inventario": ["Razioni", "Acciarino", "Otre d'acqua"],
        "mostro_attuale": {"nome": None, "hp": 0, "hp_max": 0, "status": []},
        "current_image": None, "gallery": [], "bestiario": {},
        "diario": "L'avventura ha inizio...",
        "spell_slots_max": 0, "spell_slots_curr": 0, "ultimo_tiro": None,
        "immersiva": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# --- 2. FUNZIONI DI GESTIONE ---
def registra_evento_visivo(descrizione, tipo):
    seed = random.randint(1, 99999)
    url = f"https://pollinations.ai/p/{descrizione.replace(' ', '_')}?width=1024&height=1024&nologo=true&seed={seed}"
    nuova_img = {"url": url, "caption": f"{tipo}: {descrizione[:40]}"}
    st.session_state.current_image = nuova_img
    st.session_state.gallery.append(nuova_img)
    return url

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Controllo Eroe")
    st.session_state.immersiva = st.toggle("🌌 Modalità Immersiva", value=st.session_state.immersiva)
    
    if st.session_state.game_phase != "creazione" and not st.session_state.immersiva:
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        
        # Statistiche
        st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))
        
        col1, col2 = st.columns(2)
        col1.metric("💰 Oro", f"{st.session_state.oro}g")
        col2.metric("🔮 Slot", f"{st.session_state.spell_slots_curr}")

        # Sezioni Dettagliate
        with st.expander("🎒 Inventario & Magie"):
            st.write("**Zaino:** " + ", ".join(st.session_state.inventario))
            st.write("**Abilità:** " + ", ".join(st.session_state.personaggio["abilita"]))
            if st.session_state.personaggio["incantesimi"]:
                st.write("**Incantesimi:** " + ", ".join(st.session_state.personaggio["incantesimi"]))

        with st.expander("🖼️ Galleria & Bestiario"):
            if st.session_state.gallery:
                for img in reversed(st.session_state.gallery[-3:]):
                    st.image(img["url"], caption=img["caption"])
            st.write("**Mostri Sconfitti:** " + ", ".join(st.session_state.bestiario.keys()))

        # Salvataggio
        st.divider()
        save_data = {k: v for k, v in st.session_state.items() if k not in ["GEMINI_API_KEY"]}
        st.download_button("💾 Scarica Partita (.json)", json.dumps(save_data), file_name="save_dnd.json")
        
        file_up = st.file_uploader("📂 Carica Partita", type="json")
        if file_up and st.button("Conferma Caricamento"):
            data = json.load(file_up)
            for k, v in data.items(): st.session_state[k] = v
            st.rerun()

        if st.button("🎲 Tira d20", use_container_width=True):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Hai fatto {st.session_state.ultimo_tiro}!")

    if st.button("🗑️ Reset"):
        st.session_state.clear()
        st.rerun()

# --- 4. AREA DI GIOCO ---
st.title("⚔️ D&D Legend Engine")

if st.session_state.game_phase == "creazione":
    with st.form("creazione_form"):
        nome = st.text_input("Nome Eroe")
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Chierico", "Ranger"])
        if st.form_submit_button("Inizia"):
            data_map = {
                "Guerriero": (["Secondo Vento"], [], 0),
                "Mago": (["Recupero Arcano"], ["Dardo Incantato", "Scudo"], 3),
                "Ladro": (["Attacco Furtivo"], [], 0),
                "Chierico": (["Luce Sacra"], ["Cura Ferite"], 3),
                "Ranger": (["Esploratore"], ["Marchio del Cacciatore"], 2)
            }
            abi, spells, slots = data_map[classe]
            st.session_state.personaggio = {"nome": nome, "classe": classe, "abilita": abi, "incantesimi": spells}
            st.session_state.spell_slots_max = slots
            st.session_state.spell_slots_curr = slots
            st.session_state.game_phase = "playing"
            st.rerun()

else:
    # Mostra l'immagine principale
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"])
        if not st.session_state.immersiva:
            st.caption(st.session_state.current_image["caption"])

    # Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai? (Es: Attacco il braccio destro del Goblin)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_prompt = f"""
        SEI IL DM. Giocatore: {st.session_state.personaggio}. HP: {st.session_state.hp}. Mostro: {st.session_state.mostro_attuale}. Dado: {st.session_state.ultimo_tiro}.
        USA I TAG:
        [[NUOVO_MOSTRO:Nome:HP]], [[DANNO_MOSTRO:X]], [[STATUS_MOSTRO:effetto]], [[MORTE_MOSTRO]]
        [[DANNO:X]], [[CURA:X]], [[ORO:X]], [[XP:X]], [[PRENDI:Oggetto]], [[USA_SLOT:1]]
        [[LUOGO:descrizione]], [[LOOT:descrizione]], [[DIARIO:riassunto]]
        """
        
        with st.chat_message("assistant"):
            response = model.generate_content(sys_prompt + "\n" + prompt).text
            
            # Parsing (In ordine di importanza)
            if "[[NUOVO_MOSTRO:" in response:
                d = response.split("[[NUOVO_MOSTRO:")[1].split("]]")[0].split(":")
                st.session_state.mostro_attuale = {"nome": d[0], "hp": int(d[1]), "hp_max": int(d[1]), "status": []}
                url = registra_evento_visivo(d[0], "Mostro")
                st.session_state.bestiario[d[0]] = {"img": url}
            
            if "[[DANNO_MOSTRO:" in response:
                st.session_state.mostro_attuale["hp"] -= int(response.split("[[DANNO_MOSTRO:")[1].split("]]")[0])
            
            if "[[STATUS_MOSTRO:" in response:
                st.session_state.mostro_attuale["status"].append(response.split("[[STATUS_MOSTRO:")[1].split("]]")[0])

            if "[[MORTE_MOSTRO]]" in response:
                st.session_state.mostro_attuale = {"nome": None, "hp": 0, "hp_max": 0, "status": []}

            if "[[LUOGO:" in response: registra_evento_visivo(response.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            if "[[LOOT:" in response: registra_evento_visivo(response.split("[[LOOT:")[1].split("]]")[0], "Loot")
            
            # Meccaniche Personaggio
            if "[[DANNO:" in response: st.session_state.hp -= int(response.split("[[DANNO:")[1].split("]]")[0])
            if "[[ORO:" in response: st.session_state.oro += int(response.split("[[ORO:")[1].split("]]")[0])
            if "[[XP:" in response: st.session_state.xp += int(response.split("[[XP:")[1].split("]]")[0])
            if "[[PRENDI:" in response: st.session_state.inventario.append(response.split("[[PRENDI:")[1].split("]]")[0])
            if "[[USA_SLOT:" in response: st.session_state.spell_slots_curr = max(0, st.session_state.spell_slots_curr - 1)

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
