import streamlit as st
import google.generativeai as genai
import random
import json
import os
import urllib.parse  # Essenziale per correggere il problema delle immagini

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="centered", initial_sidebar_state="collapsed")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. FUNZIONI TECNICHE ---
def tira_statistica():
    return sum(sorted([random.randint(1, 6) for _ in range(4)])[1:])

def calcola_mod(punteggio):
    return (punteggio - 10) // 2

def genera_img(descrizione, tipo):
    seed = random.randint(1, 99999)
    # Creiamo un prompt descrittivo pulito
    prompt_base = f"Dungeons and Dragons high fantasy style, {tipo}: {descrizione}, detailed digital art, 8k"
    # TRUCCO TECNICO: Encoding dell'URL per evitare simboli strani o rotture
    prompt_encoded = urllib.parse.quote(prompt_base)
    
    url = f"https://pollinations.ai/p/{prompt_encoded}?width=1024&height=1024&seed={seed}&nologo=true"
    
    img_data = {"url": url, "caption": f"{tipo}: {descrizione[:30]}..."}
    st.session_state.current_image = img_data
    st.session_state.gallery.append(img_data)
    return url

# --- 2. LOGICA XP & LIVELLO ---
SOGLIE_XP = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}
DADI_VITA = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}

def check_level_up():
    current_lv = st.session_state.livello
    next_lv = current_lv + 1
    if next_lv in SOGLIE_XP and st.session_state.xp >= SOGLIE_XP[next_lv]:
        st.session_state.livello = next_lv
        classe = st.session_state.personaggio["classe"]
        mod_cos = calcola_mod(st.session_state.personaggio["stats"]["Costituzione"])
        st.session_state.hp_max += (DADI_VITA[classe] // 2 + 1) + mod_cos
        st.session_state.hp = st.session_state.hp_max
        if st.session_state.spell_slots_max > 0:
            st.session_state.spell_slots_max += 1
            st.session_state.spell_slots_curr = st.session_state.spell_slots_max
        st.balloons()
        return True
    return False

# --- 3. INIZIALIZZAZIONE STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}},
        "hp": 20, "hp_max": 20, "oro": 0, "xp": 0, "livello": 1,
        "inventario": [], "missioni": [], "diario": "L'avventura ha inizio...",
        "current_image": None, "gallery": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None
    })

# --- 4. SIDEBAR (SCHEDA EROE) ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        
        prossima = SOGLIE_XP.get(st.session_state.livello + 1, "MAX")
        if prossima != "MAX":
            prog = (st.session_state.xp - SOGLIE_XP[st.session_state.livello]) / (prossima - SOGLIE_XP[st.session_state.livello])
            st.caption(f"XP: {st.session_state.xp} / {prossima}")
            st.progress(max(0.0, min(1.0, prog)))

        st.metric("Punti Vita", f"{st.session_state.hp}/{st.session_state.hp_max}")
        st.metric("Oro", f"{st.session_state.oro}g")
        
        with st.expander("📊 Caratteristiche"):
            for stat, val in p['stats'].items():
                st.write(f"**{stat}**: {val} ({calcola_mod(val):+})")

        with st.expander("🖼️ Galleria Immagini"):
            for img in reversed(st.session_state.gallery):
                st.image(img["url"], caption=img["caption"])

        st.divider()
        save_data = json.dumps({k: v for k, v in st.session_state.items() if k != "GEMINI_API_KEY"})
        st.download_button("💾 Backup per Smartphone", save_data, file_name="dnd_save.json", use_container_width=True)

    if st.button("🗑️ Reset Totale"):
        st.session_state.clear()
        st.rerun()

# --- 5. FLUSSO DI GIOCO ---
st.title("⚔️ D&D Legend Engine 2026")

if st.session_state.game_phase == "creazione" and not st.session_state.personaggio.get("nome"):
    st.subheader("Benvenuto, viandante")
    
    up_file = st.file_uploader("📂 Carica salvataggio .json dal telefono", type="json")
    if up_file:
        data = json.load(up_file)
        for k, v in data.items(): st.session_state[k] = v
        st.success("Avventura ripristinata!")
        st.rerun()
    
    st.divider()
    with st.form("creazione_nuova"):
        st.write("Oppure crea un nuovo eroe:")
        nome = st.text_input("Nome dell'Eroe")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
        if st.form_submit_button("Inizia Avventura") and nome:
            setup = {"Guerriero": (12,0,["Spada"]), "Mago": (6,3,["Bastone"]), "Ladro": (8,0,["Pugnali"]), "Ranger": (10,2,["Arco"]), "Chierico": (8,3,["Mazza"])}
            hp_b, slots, inv = setup[classe]
            stats = {k: tira_statistica() for k in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.session_state.update({
                "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": stats},
                "hp_max": hp_b + calcola_mod(stats["Costituzione"]), "hp": hp_b + calcola_mod(stats["Costituzione"]),
                "inventario": inv, "spell_slots_max": slots, "spell_slots_curr": slots, "game_phase": "playing"
            })
            res = model.generate_content(f"DM. Introduci l'avventura per {nome}, {razza} {classe}. Usa [[LUOGO:ambientazione]].").text
            if "[[LUOGO:" in res: genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.rerun()

else:
    # 1. Visualizzazione Immagine Corrente (Corretta)
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"], use_container_width=True)
    
    # 2. Pannello Azioni Rapide
    st.write("### Azioni Rapide")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🎲 d20"):
        st.session_state.ultimo_tiro = random.randint(1, 20)
        st.toast(f"Tiro d20: {st.session_state.ultimo_tiro}")
    
    if c2.button("🗡️ Attacco"):
        tiro = random.randint(1, 20)
        mod = calcola_mod(st.session_state.personaggio["stats"].get("Forza", 10))
        st.session_state.ultimo_tiro = tiro + mod
        st.toast(f"Attacco: {tiro} + {mod} = {st.session_state.ultimo_tiro}")
        
    if c3.button("✨ Magia"):
        if st.session_state.spell_slots_curr > 0:
            st.session_state.spell_slots_curr -= 1
            tiro = random.randint(1, 20)
            mod = calcola_mod(st.session_state.personaggio["stats"].get("Intelligenza", 10))
            st.session_state.ultimo_tiro = tiro + mod
            st.toast(f"Magia! Risultato: {st.session_state.ultimo_tiro}")
        else:
            st.error("Slot esauriti!")

    if c4.button("⛺ Riposo"):
        st.session_state.hp = st.session_state.hp_max
        st.session_state.spell_slots_curr = st.session_state.spell_slots_max
        st.success("Riposo completato!")

    st.divider()

    # 3. Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_p = f"""Sei un DM di D&D. PG: {st.session_state.personaggio}. HP: {st.session_state.hp}/{st.session_state.hp_max}.
        Usa SEMPRE questi tag:
        - [[LUOGO:desc]], [[MOSTRO:desc]], [[OGGETTO:desc]]
        - [[DANNO:n]], [[ORO:n]], [[XP:n]], [[DIARIO:testo]]
        Usa il tiro dado ({st.session_state.ultimo_tiro}) se presente."""

        with st.chat_message("assistant"):
            full_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
            response = model.generate_content(sys_p + "\n" + full_history).text
            
            # Parsing Tag
            tags = {"[[LUOGO:": "Luogo", "[[MOSTRO:": "Mostro", "[[OGGETTO:": "Oggetto"}
            for tag, label in tags.items():
                if tag in response: genera_img(response.split(tag)[1].split("]]")[0], label)
            
            if "[[DANNO:" in response: 
                d = int(response.split("[[DANNO:")[1].split("]]")[0])
                st.session_state.hp = max(0, min(st.session_state.hp_max, st.session_state.hp - d))
            if "[[ORO:" in response: st.session_state.oro += int(response.split("[[ORO:")[1].split("]]")[0])
            if "[[XP:" in response: 
                st.session_state.xp += int(response.split("[[XP:")[1].split("]]")[0])
                if check_level_up(): st.toast("✨ LIVELLO AUMENTATO!")
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
