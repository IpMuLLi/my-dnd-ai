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
    return sum(sorted([random.randint(1, 6) for _ in range(4)])[1:])

def init_state():
    defaults = {
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "abilita": [], "incantesimi": []},
        "hp": 20, "hp_max": 20, "oro": 0, "xp": 0, "livello": 1,
        "inventario": [], "missioni": [],
        "mostro_attuale": {"nome": None, "hp": 0, "hp_max": 0, "status": []},
        "current_image": None, "gallery": [], "bestiario": {},
        "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "immersiva": False
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

init_state()

# --- 2. LOGICA VISIVA ---
def genera_img(descrizione, tipo):
    seed = random.randint(1, 99999)
    url = f"https://pollinations.ai/p/{descrizione.replace(' ', '_')}?width=1024&height=1024&seed={seed}&nologo=true"
    img_data = {"url": url, "caption": f"{tipo}: {descrizione[:30]}"}
    st.session_state.current_image = img_data
    st.session_state.gallery.append(img_data)
    return url

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    st.session_state.immersiva = st.toggle("🌌 Modalità Immersiva", st.session_state.immersiva)
    
    if st.session_state.game_phase != "creazione" and not st.session_state.immersiva:
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        
        # Statistiche
        st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
        s = st.session_state.personaggio['stats']
        st.caption(f"FOR:{s.get('Forza')} DES:{s.get('Destrezza')} COS:{s.get('Costituzione')} INT:{s.get('Intelligenza')} SAG:{s.get('Saggezza')} CAR:{s.get('Carisma')}")
        
        st.divider()
        
        # Missioni
        if st.session_state.missioni:
            st.subheader("📜 Missioni")
            for m in st.session_state.missioni:
                st.info(f"📍 {m}")

        # Zaino (FIX: Visualizzazione pulita e completa)
        with st.expander("🎒 Zaino & Equipaggiamento", expanded=True):
            st.write(f"💰 **Oro:** {st.session_state.oro}g")
            if st.session_state.inventario:
                for item in st.session_state.inventario:
                    st.write(f"• {item}")
            else:
                st.write("Lo zaino è vuoto.")
        
        # Poteri
        with st.expander("✨ Abilità & Magie"):
            st.write("**Abilità:** " + ", ".join(st.session_state.personaggio['abilita']))
            if st.session_state.personaggio['incantesimi']:
                st.write("**Magie:** " + ", ".join(st.session_state.personaggio['incantesimi']))
                st.write(f"🔮 Slot: {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
        
        # Galleria
        if st.session_state.gallery:
            with st.expander("🖼️ Galleria"):
                for img in reversed(st.session_state.gallery[-3:]):
                    st.image(img["url"])

        st.divider()
        # Salvataggio
        save_data = {k: v for k, v in st.session_state.items() if k not in ["GEMINI_API_KEY"]}
        st.download_button("💾 Salva JSON", json.dumps(save_data), file_name="save.json", use_container_width=True)
        
        up = st.file_uploader("📂 Carica JSON", type="json")
        if up and st.button("Conferma Caricamento"):
            data = json.load(up)
            for k, v in data.items(): st.session_state[k] = v
            st.rerun()

    if st.button("🗑️ Reset Totale", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 4. GIOCO ---
if st.session_state.game_phase == "creazione":
    with st.form("creazione"):
        nome = st.text_input("Nome")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling"])
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
        if st.form_submit_button("Inizia Avventura") and nome:
            # FIX DEFINITIVO: Allineamento nomi oggetti con la narrazione
            setup = {
                "Guerriero": (12, 0, ["Spada Lunga", "Scudo", "Cotta di Maglia", "Razioni"], ["Azione Impetuosa"], []),
                "Mago": (6, 3, ["Bastone Arcano", "Libro Incantesimi", "Razioni"], ["Recupero Arcano"], ["Dardo Incantato", "Scudo"]),
                "Ladro": (8, 0, ["2 Pugnali", "Attrezzi da scasso", "Armatura di Cuoio", "Razioni"], ["Attacco Furtivo"], []),
                "Ranger": (10, 2, ["Arco Lungo", "Faretra (20 frecce)", "Spada Corta", "Armatura di Cuoio", "Razioni"], ["Esploratore"], ["Marchio"]),
                "Chierico": (8, 3, ["Mazza", "Simbolo Sacro", "Armatura di Scaglie", "Razioni"], ["Luce Sacra"], ["Cura Ferite"])
            }
            hp_b, slots, inv, abi, spells = setup[classe]
            st.session_state.personaggio = {
                "nome": nome, "classe": classe, "razza": razza,
                "stats": {k: tira_statistica() for k in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]},
                "abilita": abi, "incantesimi": spells
            }
            st.session_state.hp_max = hp_b
            st.session_state.hp = hp_b
            st.session_state.inventario = inv
            st.session_state.oro = random.randint(50, 100)
            st.session_state.spell_slots_max = slots
            st.session_state.spell_slots_curr = slots
            st.session_state.game_phase = "playing"
            
            incipit = f"Inizia avventura per {nome} ({razza} {classe}). Tag: [[LUOGO:ambientazione]], [[MISSIONE:Inizio]]"
            res = model.generate_content(incipit).text
            if "[[LUOGO:" in res: genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            if "[[MISSIONE:" in res: st.session_state.missioni = [res.split("[[MISSIONE:")[1].split("]]")[0]]
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.rerun()
else:
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"])
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if pr := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": pr})
        sys = f"DM. Eroe: {st.session_state.personaggio}. HP: {st.session_state.hp}. Usa i tag: [[DANNO:X]], [[ORO:X]], [[PRENDI:Oggetto]], [[LUOGO:descrizione]], [[MISSIONE:nome]]"
        with st.chat_message("assistant"):
            r = model.generate_content(sys + "\n" + pr).text
            
            if "[[PRENDI:" in r:
                oggetto = r.split("[[PRENDI:")[1].split("]]")[0]
                st.session_state.inventario.append(oggetto)
            
            if "[[LUOGO:" in r: genera_img(r.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            
            st.markdown(r)
            st.session_state.messages.append({"role": "assistant", "content": r})
            st.rerun()
            
