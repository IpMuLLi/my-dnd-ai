import streamlit as st
import google.generativeai as genai
import random
import json
import os
import urllib.parse

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="centered", initial_sidebar_state="collapsed")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. FUNZIONI TECNICHE ---
def tira_statistica():
    dadi = [random.randint(1, 6) for _ in range(4)]
    dadi.remove(min(dadi))
    return sum(dadi)

def calcola_mod(punteggio):
    return (punteggio - 10) // 2

def genera_img(descrizione, tipo):
    try:
        seed = random.randint(1, 99999)
        prompt_base = f"Dungeons and Dragons high fantasy, {tipo}: {descrizione}, cinematic lighting, detailed digital art, 8k"
        prompt_encoded = urllib.parse.quote(prompt_base)
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
        img_data = {"url": url, "caption": f"{tipo}: {descrizione[:30]}..."}
        st.session_state.current_image = img_data
        st.session_state.gallery.append(img_data)
        return url
    except: return None

# --- 2. LOGICA AVANZATA ---
SOGLIE_XP = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}
DADI_VITA = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}
COMPETENZE = {
    "Guerriero": "Atletica, Percezione", "Mago": "Arcano, Storia",
    "Ladro": "Furtività, Rapidità di mano", "Ranger": "Sopravvivenza, Natura",
    "Chierico": "Intuizione, Religione"
}

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

# --- 3. INIZIALIZZAZIONE ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1,
        "inventario": [], "condizioni": [], "diario": "L'avventura ha inizio...",
        "current_image": None, "gallery": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "cronologia_eventi": "", "temp_stats": {}, "sommario": ""
    })

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        st.metric("Punti Vita ❤️", f"{st.session_state.hp}/{st.session_state.hp_max}")
        st.metric("Oro 🪙", f"{st.session_state.oro}gp")
        
        if st.session_state.condizioni:
            st.warning(f"⚠️ {', '.join(st.session_state.condizioni)}")

        with st.expander("📊 Statistiche & Abilità"):
            for stat, val in st.session_state.personaggio['stats'].items():
                st.write(f"**{stat}**: {val} ({calcola_mod(val):+})")
            st.caption(f"Competenze: {COMPETENZE.get(st.session_state.personaggio['classe'])}")

        if st.button("📜 Genera Sommario Sessione"):
            with st.spinner("Il bardo sta scrivendo..."):
                prompt_sommario = f"Basandoti su questo diario: {st.session_state.diario}, scrivi un riassunto epico e breve per riprendere la sessione."
                st.session_state.sommario = model.generate_content(prompt_sommario).text
        
        if st.session_state.sommario:
            st.info(st.session_state.sommario)

        st.divider()
        save_data = json.dumps({k: v for k, v in st.session_state.items() if k != "GEMINI_API_KEY"})
        st.download_button("💾 Esporta Salvataggio", save_data, file_name="dnd_save.json", use_container_width=True)

    if st.button("🗑️ Reset"):
        st.session_state.clear()
        st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Creazione Eroe")
    if not st.session_state.temp_stats:
        if st.button("Lancia i Dadi per le Statistiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        cols = st.columns(3)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i%3].metric(s, v)
        
        with st.form("completamento"):
            nome = st.text_input("Nome")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Crea") and nome:
                setup = {"Guerriero": (12,0,["Spada"]), "Mago": (6,3,["Bastone"]), "Ladro": (8,0,["Daga"]), "Ranger": (10,2,["Arco"]), "Chierico": (8,3,["Mazza"])}
                hp_b, slots, inv = setup[classe]
                st.session_state.update({
                    "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": st.session_state.temp_stats},
                    "hp_max": hp_b + calcola_mod(st.session_state.temp_stats["Costituzione"]), "hp": hp_b + calcola_mod(st.session_state.temp_stats["Costituzione"]),
                    "inventario": inv, "spell_slots_max": slots, "spell_slots_curr": slots, "game_phase": "playing"
                })
                st.rerun()
else:
    st.title("⚔️ D&D Legend Engine 2026")
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"], use_container_width=True)

    # Azioni Rapide
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🎲 d20"):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Tiro: {st.session_state.ultimo_tiro}")
    with c2:
        if st.button("🗡️ Attacco"):
            mod = calcola_mod(st.session_state.personaggio["stats"]["Forza"])
            st.session_state.ultimo_tiro = random.randint(1, 20) + mod + 2
            st.toast(f"Attacco: {st.session_state.ultimo_tiro}")
    with c3:
        if st.button("✨ Magia"):
            if st.session_state.spell_slots_curr > 0:
                st.session_state.spell_slots_curr -= 1
                st.session_state.ultimo_tiro = random.randint(1, 20) + 4
                st.toast("Incantesimo lanciato!")
            else: st.error("No slot!")
    with c4:
        if st.button("⛺ Riposo"):
            st.session_state.hp = st.session_state.hp_max
            st.session_state.spell_slots_curr = st.session_state.spell_slots_max
            st.success("Ripristinato!")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        sys_p = f"Sei il DM. PG: {st.session_state.personaggio}. Tiro: {st.session_state.ultimo_tiro}. Tag: [[LUOGO:desc]], [[DANNO:n]], [[ORO:n]], [[DIARIO:testo]]."
        with st.chat_message("assistant"):
            response = model.generate_content(sys_p + "\n" + prompt).text
            if "[[DIARIO:" in response:
                st.session_state.diario += "\n" + response.split("[[DIARIO:")[1].split("]]")[0]
            if "[[DANNO:" in response:
                st.session_state.hp -= int(response.split("[[DANNO:")[1].split("]]")[0])
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
