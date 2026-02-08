import streamlit as st
import google.generativeai as genai
import random
import json
import os
import urllib.parse
import re

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="centered", initial_sidebar_state="collapsed")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

# Configurazione del modello di punta 2026
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. FUNZIONI TECNICHE (PRESERVATE) ---
def tira_statistica():
    dadi = [random.randint(1, 6) for _ in range(4)]
    dadi.sort()
    return sum(dadi[1:])

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

# --- 2. LOGICA XP & LIVELLO (PRESERVATA) ---
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
        st.toast(f"✨ LIVELLO AUMENTATO! Sei ora Livello {st.session_state.livello}", icon="🛡️")
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

# --- 4. SIDEBAR (COMPLETA) ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.personaggio.get("nome"):
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        st.metric("Punti Vita ❤️", f"{st.session_state.hp}/{st.session_state.hp_max}")
        st.metric("Oro 🪙", f"{st.session_state.oro}gp")
        st.caption(f"Esperienza (XP): {st.session_state.xp}")
        
        with st.expander("📊 Statistiche & Abilità"):
            for stat, val in st.session_state.personaggio['stats'].items():
                st.write(f"**{stat}**: {val} ({calcola_mod(val):+})")
            st.caption(f"Competenze: {COMPETENZE.get(st.session_state.personaggio['classe'])}")

        with st.expander("🎒 Equipaggiamento"):
            if st.session_state.inventario:
                for item in st.session_state.inventario: st.write(f"- {item}")
            else: st.write("Zaino vuoto.")

        if st.session_state.spell_slots_max > 0:
            with st.expander("✨ Magia"):
                st.write(f"Slot rimanenti: {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
                st.progress(st.session_state.spell_slots_curr / st.session_state.spell_slots_max)

        with st.expander("🖼️ Galleria Immagini"):
            for img in reversed(st.session_state.gallery):
                st.image(img["url"], caption=img["caption"])

        st.divider()
        if st.button("📜 Genera Sommario Sessione"):
            with st.spinner("Scrivendo..."):
                st.session_state.sommario = model.generate_content(f"Riassumi epicamente e brevemente: {st.session_state.diario}").text
        if st.session_state.sommario: st.info(st.session_state.sommario)

        save_data = json.dumps({k: v for k, v in st.session_state.items() if k != "GEMINI_API_KEY"})
        st.download_button("💾 Esporta Salvataggio", save_data, file_name="dnd_save.json", use_container_width=True)

    if st.button("🗑️ Reset"):
        st.session_state.clear()
        st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Creazione Personaggio")
    
    with st.expander("📂 Carica Personaggio Esistente"):
        up_file = st.file_uploader("Carica .json", type="json")
        if up_file:
            data = json.load(up_file)
            for k, v in data.items(): st.session_state[k] = v
            st.rerun()

    if not st.session_state.temp_stats:
        if st.button("🎲 Lancia Caratteristiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        cols = st.columns(3)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i%3].metric(s, v)
        
        if st.button("🔄 Reroll"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()

        with st.form("creazione_finale"):
            nome = st.text_input("Nome")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia Avventura") and nome:
                setup = {"Guerriero": (12,0,["Spada", "Armatura"]), "Mago": (6,3,["Bastone", "Pergamena"]), "Ladro": (8,0,["Daghe"]), "Ranger": (10,2,["Arco"]), "Chierico": (8,3,["Mazza"])}
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

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
    if c2.button("🗡️ Attacco"): st.session_state.ultimo_tiro = random.randint(1, 20) + calcola_mod(st.session_state.personaggio["stats"]["Forza"]) + 2
    if c3.button("✨ Magia"):
        if st.session_state.spell_slots_curr > 0:
            st.session_state.spell_slots_curr -= 1
            st.session_state.ultimo_tiro = random.randint(1, 20) + 4
        else: st.error("Slot esauriti!")
    if c4.button("⛺ Riposo"):
        st.session_state.hp = st.session_state.hp_max
        st.session_state.spell_slots_curr = st.session_state.spell_slots_max
        st.success("Ripristinato!")

    if st.session_state.ultimo_tiro:
        st.write(f"🎲 Ultimo Tiro: **{st.session_state.ultimo_tiro}**")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # --- PROMPT DI SISTEMA AVANZATO 2026 ---
        sys_p = f"""Sei un DM di D&D 5e esperto. Anno 2026.
        Dati PG: {st.session_state.personaggio}. 
        HP: {st.session_state.hp}/{st.session_state.hp_max}. Oro: {st.session_state.oro}. XP: {st.session_state.xp}.
        Tiro Corrente: {st.session_state.ultimo_tiro if st.session_state.ultimo_tiro else 'Nessuno - Chiedi un tiro se necessario'}.

        REGOLE DI RISOLUZIONE:
        1. Se Tiro < 10: Fallimento o complicazione.
        2. Se Tiro 10-14: Successo con costo o complicazione minore.
        3. Se Tiro 15-19: Successo pieno.
        4. Se Tiro 20+: Successo critico epico.
        5. Se Tiro è 'Nessuno' e l'azione richiede rischio, descrivi l'intento e chiedi un d20.
        6. DANNO PG: Coerente col livello {st.session_state.livello} (es. 1d6+2). Mai One-Shot ingiustificati.

        TAG OBBLIGATORI (da includere nel testo):
        [[LUOGO:descrizione]] per nuove scene.
        [[DANNO:n]] se il PG perde vita.
        [[ORO:n]] per guadagno/perdita oro.
        [[XP:n]] per ricompense XP.
        [[ITEM:nome]] per nuovi oggetti.
        [[DIARIO:testo]] per la cronaca.
        """
        
        with st.chat_message("assistant"):
            full_res = model.generate_content(sys_p + "\n" + prompt).text
            
            # Parsing con Regex per massima precisione
            if "[[LUOGO:" in full_res: 
                loc = full_res.split("[[LUOGO:")[1].split("]]")[0]
                genera_img(loc, "Luogo")
            
            danno = re.search(r'\[\[DANNO:(\d+)\]\]', full_res)
            if danno: st.session_state.hp -= int(danno.group(1))
            
            oro = re.search(r'\[\[ORO:(-?\d+)\]\]', full_res)
            if oro: st.session_state.oro += int(oro.group(1))
            
            xp = re.search(r'\[\[XP:(\d+)\]\]', full_res)
            if xp: 
                st.session_state.xp += int(xp.group(1))
                check_level_up()
                
            item = re.search(r'\[\[ITEM:(.*?)\]\]', full_res)
            if item: st.session_state.inventario.append(item.group(1).strip())
            
            if "[[DIARIO:" in full_res: 
                st.session_state.diario += "\n" + full_res.split("[[DIARIO:")[1].split("]]")[0]
            
            clean_res = re.sub(r'\[\[.*?\]\]', '', full_res).strip()
            st.markdown(clean_res)
            st.session_state.messages.append({"role": "assistant", "content": clean_res})
            
            # Reset del tiro dopo la risoluzione
            st.session_state.ultimo_tiro = None
            st.rerun()
            
