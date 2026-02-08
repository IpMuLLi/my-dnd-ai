import streamlit as st
import google.generativeai as genai
import random
import json

# --- CONFIGURAZIONE CORE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. FUNZIONI TECNICHE ---
def tira_statistica():
    return sum(sorted([random.randint(1, 6) for _ in range(4)])[1:])

def genera_img(descrizione, tipo):
    seed = random.randint(1, 99999)
    url = f"https://pollinations.ai/p/{descrizione.replace(' ', '_')}?width=1024&height=1024&seed={seed}&nologo=true"
    img_data = {"url": url, "caption": f"{tipo}: {descrizione[:30]}"}
    st.session_state.current_image = img_data
    st.session_state.gallery.append(img_data)
    return url

# --- 2. INIZIALIZZAZIONE STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "abilita": [], "incantesimi": []},
        "hp": 20, "hp_max": 20, "oro": 0, "xp": 0, "livello": 1,
        "inventario": [], "missioni": [], "diario": "L'avventura sta per iniziare...",
        "current_image": None, "gallery": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "immersiva": False
    })

# --- 3. SIDEBAR (LA SCHEDA EROE) ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    st.session_state.immersiva = st.toggle("🌌 Modalità Immersiva", st.session_state.immersiva)
    
    if st.session_state.game_phase != "creazione" and not st.session_state.immersiva:
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        
        # Statistiche e Vita
        st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
        st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))
        
        # Caratteristiche
        s = st.session_state.personaggio['stats']
        st.caption(f"FOR:{s.get('Forza')} | DES:{s.get('Destrezza')} | COS:{s.get('Costituzione')}")
        st.caption(f"INT:{s.get('Intelligenza')} | SAG:{s.get('Saggezza')} | CAR:{s.get('Carisma')}")

        # Diario e Missioni
        with st.expander("📖 Diario & Missioni", expanded=True):
            st.write("**Obiettivi:**")
            for m in st.session_state.missioni: st.info(f"📍 {m}")
            st.write("**Riassunto:**")
            st.caption(st.session_state.diario)

        # Equipaggiamento Completo
        with st.expander("🎒 Zaino & Poteri"):
            st.write(f"💰 Oro: {st.session_state.oro}g")
            st.write("**Oggetti:**")
            for item in st.session_state.inventario: st.write(f"• {item}")
            st.write("**Abilità:** " + ", ".join(st.session_state.personaggio['abilita']))
            if st.session_state.personaggio['incantesimi']:
                st.write(f"🔮 Slot: {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")

        # Sistema di Salvataggio
        st.divider()
        save_dict = {k: v for k, v in st.session_state.items() if k not in ["GEMINI_API_KEY"]}
        st.download_button("💾 Esporta Salvataggio", json.dumps(save_dict), file_name="dnd_save.json", use_container_width=True)
        
        up = st.file_uploader("📂 Carica JSON", type="json")
        if up and st.button("Ripristina"):
            data = json.load(up)
            for k, v in data.items(): st.session_state[k] = v
            st.rerun()

        if st.button("🎲 Tira d20", use_container_width=True):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Risultato: {st.session_state.ultimo_tiro}")

    if st.button("🗑️ Reset"):
        st.session_state.clear()
        st.rerun()

# --- 4. FLUSSO DI GIOCO ---
st.title("⚔️ D&D Legend Engine 2026")

if st.session_state.game_phase == "creazione":
    
    with st.form("char_creation"):
        nome = st.text_input("Nome dell'Eroe")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
        if st.form_submit_button("Crea il tuo Destino") and nome:
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
            st.session_state.hp_max = hp_b + (st.session_state.personaggio["stats"]["Costituzione"] // 2 - 5)
            st.session_state.hp = st.session_state.hp_max
            st.session_state.inventario = inv
            st.session_state.oro = random.randint(30, 100)
            st.session_state.spell_slots_max = slots
            st.session_state.spell_slots_curr = slots
            st.session_state.game_phase = "playing"
            
            # Inizio Automatico
            incipit = f"Inizia un'avventura per {nome}, {razza} {classe}. Tag: [[LUOGO:ambientazione]], [[MISSIONE:nome]]"
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

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Memoria: Passiamo a Gemini il diario + le ultime azioni
        context = f"DIARIO: {st.session_state.diario}\n"
        sys_p = f"DM. Eroe: {st.session_state.personaggio}. HP: {st.session_state.hp}. Zaino: {st.session_state.inventario}. Usa [[DANNO:X]], [[PRENDI:Ogg]], [[DIARIO:riassunto]], [[MISSIONE:nome]]."
        
        with st.chat_message("assistant"):
            full_prompt = context + "\n".join([m["content"] for m in st.session_state.messages[-5:]])
            response = model.generate_content(sys_p + full_prompt).text
            
            # Parsing Meccanico
            if "[[PRENDI:" in response: st.session_state.inventario.append(response.split("[[PRENDI:")[1].split("]]")[0])
            if "[[DANNO:" in response: st.session_state.hp -= int(response.split("[[DANNO:")[1].split("]]")[0])
            if "[[DIARIO:" in response: st.session_state.diario = response.split("[[DIARIO:")[1].split("]]")[0]
            if "[[LUOGO:" in response: genera_img(response.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            if "[[MISSIONE:" in response: st.session_state.missioni.append(response.split("[[MISSIONE:")[1].split("]]")[0])
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
            
