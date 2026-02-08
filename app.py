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

# --- 1. INIZIALIZZAZIONE SICURA ---
def tira_statistica():
    return sum(sorted([random.randint(1, 6) for _ in range(4)])[1:])

def init_state():
    defaults = {
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "abilita": [], "incantesimi": []},
        "hp": 20, "hp_max": 20, "oro": 0, "xp": 0, "livello": 1,
        "inventario": [], "missioni": ["Inizia l'avventura"],
        "mostro_attuale": {"nome": None, "hp": 0, "hp_max": 0, "status": []},
        "current_image": None, "gallery": [], "bestiario": {},
        "diario": "L'avventura ha inizio...", "spell_slots_max": 0, "spell_slots_curr": 0,
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
        
        # Statistiche Vitali
        st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))

        # Caratteristiche
        s = st.session_state.personaggio['stats']
        st.caption(f"FOR: {s.get('Forza')} | DES: {s.get('Destrezza')} | COS: {s.get('Costituzione')}")
        st.caption(f"INT: {s.get('Intelligenza')} | SAG: {s.get('Saggezza')} | CAR: {s.get('Carisma')}")
        
        st.divider()
        
        # Missioni Attive
        st.subheader("📜 Missioni")
        for m in st.session_state.missioni:
            st.info(f"📍 {m}")

        # Equipaggiamento e Poteri
        with st.expander("🎒 Zaino & Magie"):
            st.write(f"💰 Oro: {st.session_state.oro}g")
            st.write("**Zaino:** " + ", ".join(st.session_state.inventario))
            st.write("**Abilità:** " + ", ".join(st.session_state.personaggio['abilita']))
            if st.session_state.personaggio['incantesimi']:
                st.write("**Magie:** " + ", ".join(st.session_state.personaggio['incantesimi']))
                st.write(f"🔮 Slot: {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
        
        # Galleria
        if st.session_state.gallery:
            with st.expander("🖼️ Galleria Immagini"):
                for img in reversed(st.session_state.gallery[-3:]):
                    st.image(img["url"], caption=img["caption"])
        
        st.divider()

        # Salvataggi
        col_s1, col_s2 = st.columns(2)
        save_data = {k: v for k, v in st.session_state.items() if k not in ["GEMINI_API_KEY"]}
        col_s1.download_button("💾 Salva", json.dumps(save_data), file_name="save.json")
        
        up = st.file_uploader("📂 Carica", type="json")
        if up and st.button("Conferma Caricamento"):
            data = json.load(up)
            for k, v in data.items(): st.session_state[k] = v
            st.rerun()

        if st.button("🎲 Tira d20", use_container_width=True):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Hai fatto {st.session_state.ultimo_tiro}!")

    if st.button("🗑️ Reset Totale", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 4. GIOCO ---
if st.session_state.game_phase == "creazione":
    st.subheader("Creazione Personaggio")
    with st.form("creazione"):
        nome = st.text_input("Nome dell'Eroe")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
        if st.form_submit_button("Inizia l'Avventura") and nome:
            setup = {
                "Guerriero": (12, 0, ["Spada", "Scudo"], ["Azione Impetuosa"], []),
                "Mago": (6, 3, ["Bastone"], ["Recupero Arcano"], ["Dardo Incantato", "Scudo"]),
                "Ladro": (8, 0, ["Pugnali", "Attrezzi da scasso"], ["Attacco Furtivo"], []),
                "Ranger": (10, 2, ["Arco", "Spada"], ["Esploratore"], ["Marchio"]),
                "Chierico": (8, 3, ["Mazza", "Simbolo Sacro"], ["Luce Sacra"], ["Cura Ferite"])
            }
            hp_b, slots, inv, abi, spells = setup[classe]
            st.session_state.personaggio = {
                "nome": nome, "classe": classe, "razza": razza,
                "stats": {k: tira_statistica() for k in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]},
                "abilita": abi, "incantesimi": spells
            }
            st.session_state.hp_max = hp_b + (st.session_state.personaggio["stats"]["Costituzione"] // 2 - 5)
            st.session_state.hp = st.session_state.hp_max
            st.session_state.inventario = inv
            st.session_state.oro = random.randint(20, 100)
            st.session_state.spell_slots_max = slots
            st.session_state.spell_slots_curr = slots
            st.session_state.game_phase = "playing"
            
            incipit = f"Inizia un'avventura epica per un {razza} {classe} di nome {nome}. Usa [[LUOGO:ambientazione]] e definisci la prima missione con [[MISSIONE:nome missione]]."
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
        sys = f"DM. Eroe: {st.session_state.personaggio}. HP: {st.session_state.hp}. Dado: {st.session_state.ultimo_tiro}. Usa [[LUOGO:...]], [[MOSTRO:...]], [[LOOT:...]], [[MISSIONE:nuova missione]], [[COMPLETA_MISSIONE:nome]]"
        with st.chat_message("assistant"):
            r = model.generate_content(sys + "\n" + pr).text
            
            # Parsing Immagini
            if "[[LUOGO:" in r: genera_img(r.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            if "[[MOSTRO:" in r: genera_img(r.split("[[MOSTRO:")[1].split("]]")[0], "Mostro")
            
            # Parsing Missioni
            if "[[MISSIONE:" in r:
                nuova_m = r.split("[[MISSIONE:")[1].split("]]")[0]
                if nuova_m not in st.session_state.missioni: st.session_state.missioni.append(nuova_m)
            if "[[COMPLETA_MISSIONE:" in r:
                m_fatta = r.split("[[COMPLETA_MISSIONE:")[1].split("]]")[0]
                st.session_state.missioni = [m for m in st.session_state.missioni if m_fatta not in m]

            # Meccaniche (Danno/Cura/Oro)
            if "[[DANNO:" in r: st.session_state.hp -= int(r.split("[[DANNO:")[1].split("]]")[0])
            if "[[ORO:" in r: st.session_state.oro += int(r.split("[[ORO:")[1].split("]]")[0])
            
            st.markdown(r)
            st.session_state.messages.append({"role": "assistant", "content": r})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
