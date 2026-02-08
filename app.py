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

# Modello Gemini 2.5 Flash
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

# --- 2. LOGICA XP, LIVELLO & ABILITÀ (EVOLUTA) ---
SOGLIE_XP = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}
DADI_VITA = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}

# Mappatura Abilità su Statistiche (SRD 5e)
SKILL_MAP = {
    "Atletica": "Forza", "Furtività": "Destrezza", "Rapidità di mano": "Destrezza",
    "Arcano": "Intelligenza", "Storia": "Intelligenza", "Indagare": "Intelligenza",
    "Percezione": "Saggezza", "Intuizione": "Saggezza", "Sopravvivenza": "Saggezza",
    "Persuasione": "Carisma", "Religione": "Intelligenza", "Natura": "Intelligenza"
}

COMPETENZE_CLASSE = {
    "Guerriero": ["Atletica", "Percezione"],
    "Mago": ["Arcano", "Storia"],
    "Ladro": ["Furtività", "Rapidità di mano", "Indagare"],
    "Ranger": ["Sopravvivenza", "Percezione", "Natura"],
    "Chierico": ["Religione", "Intuizione"]
}

EQUIPAGGIAMENTO_STANDARD = {
    "Guerriero": ["Cotta di Maglia", "Spada Lunga", "Scudo", "Dotazione da Esploratore", "Arco Lungo"],
    "Mago": ["Bastone Arcano", "Libro degli Incantesimi", "Borsa per Componenti", "Dotazione da Studioso"],
    "Ladro": ["Daga x2", "Arco Corto", "Armatura di Cuoio", "Arnesi da Scasso", "Dotazione da Scassinatore"],
    "Ranger": ["Armatura di Cuoio", "Spada Corta x2", "Arco Lungo", "Dotazione da Esploratore"],
    "Chierico": ["Mazza", "Scudo", "Simbolo Sacro", "Cotta di Maglia", "Dotazione da Sacerdote"]
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
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
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
        
        with st.expander("📊 Statistiche & Abilità"):
            prof = st.session_state.bonus_competenza
            for stat, val in st.session_state.personaggio['stats'].items():
                mod = calcola_mod(val)
                st.write(f"**{stat}**: {val} ({mod:+})")
            st.divider()
            st.caption("Abilità con Competenza:")
            for skill in st.session_state.personaggio["competenze"]:
                stat_relativa = SKILL_MAP[skill]
                bonus_finale = calcola_mod(st.session_state.personaggio['stats'][stat_relativa]) + prof
                st.write(f"✅ {skill}: {bonus_finale:+}")

        with st.expander("🎒 Equipaggiamento"):
            for item in st.session_state.inventario: st.write(f"- {item}")

        if st.session_state.spell_slots_max > 0:
            with st.expander("✨ Magia"):
                st.write(f"Slot: {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
                st.progress(st.session_state.spell_slots_curr / st.session_state.spell_slots_max)

        with st.expander("🖼️ Galleria"):
            for img in reversed(st.session_state.gallery):
                st.image(img["url"], caption=img["caption"])

        if st.button("🗑️ Reset"):
            st.session_state.clear()
            st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Creazione Personaggio")
    
    if not st.session_state.temp_stats:
        if st.button("🎲 Lancia Caratteristiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        cols = st.columns(3)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i%3].metric(s, v)

        with st.form("creazione_finale"):
            nome = st.text_input("Nome dell'Eroe")
            razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            
            if st.form_submit_button("Inizia Avventura") and nome:
                slots = 3 if classe in ["Mago", "Chierico"] else (2 if classe == "Ranger" else 0)
                mod_cos = calcola_mod(st.session_state.temp_stats["Costituzione"])
                hp_tot = DADI_VITA[classe] + mod_cos
                
                st.session_state.update({
                    "personaggio": {
                        "nome": nome, "classe": classe, "razza": razza, 
                        "stats": st.session_state.temp_stats, 
                        "competenze": COMPETENZE_CLASSE[classe]
                    },
                    "hp_max": hp_tot, "hp": hp_tot,
                    "inventario": EQUIPAGGIAMENTO_STANDARD[classe],
                    "spell_slots_max": slots, "spell_slots_curr": slots,
                    "game_phase": "playing"
                })
                
                # Trigger per introduzione automatica
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"[[INTRODUZIONE]] Benvenuto, {nome} il {classe}. La tua leggenda ha inizio ora..."
                })
                st.rerun()

else:
    st.title("⚔️ D&D Legend Engine 2026")
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"], use_container_width=True)

    # Interfaccia Tiri
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🎲 d20"): st.session_state.ultimo_tiro = random.randint(1, 20)
    if c2.button("🗡️ Attacco"): 
        bonus = calcola_mod(st.session_state.personaggio["stats"]["Forza"]) + st.session_state.bonus_competenza
        st.session_state.ultimo_tiro = random.randint(1, 20) + bonus
    if c3.button("✨ Magia"):
        if st.session_state.spell_slots_curr > 0:
            st.session_state.spell_slots_curr -= 1
            st.session_state.ultimo_tiro = random.randint(1, 20) + 5
        else: st.error("Slot esauriti!")
    if c4.button("⛺ Riposo"):
        st.session_state.hp = st.session_state.hp_max
        st.session_state.spell_slots_curr = st.session_state.spell_slots_max
        st.success("Riposo Lungo completato!")

    if st.session_state.ultimo_tiro: st.info(f"🎲 Risultato del Dado: **{st.session_state.ultimo_tiro}**")

    for msg in st.session_state.messages:
        if "[[INTRODUZIONE]]" not in msg["content"]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # Se è appena iniziata la partita, genera l'intro
    if len(st.session_state.messages) == 1 and "[[INTRODUZIONE]]" in st.session_state.messages[0]["content"]:
        with st.chat_message("assistant"):
            intro_prompt = f"Sei il DM. Introduci l'inizio dell'avventura per {st.session_state.personaggio['nome']}, {st.session_state.personaggio['razza']} {st.session_state.personaggio['classe']}. Equipaggiamento: {st.session_state.inventario}. Usa il tag [[LUOGO:descrizione]] per lo scenario iniziale."
            response = model.generate_content(intro_prompt).text
            # Parsing luogo
            if "[[LUOGO:" in response:
                loc = response.split("[[LUOGO:")[1].split("]]")[0]
                genera_img(loc, "Inizio Avventura")
            clean_intro = re.sub(r'\[\[.*?\]\]', '', response).strip()
            st.markdown(clean_intro)
            st.session_state.messages[0]["content"] = clean_intro
            st.rerun()

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_p = f"""DM 5e. PG: {st.session_state.personaggio}. LV: {st.session_state.livello}. 
        Tiro: {st.session_state.ultimo_tiro if st.session_state.ultimo_tiro else 'Nessuno'}.
        Usa: [[LUOGO:desc]], [[DANNO:n]], [[ORO:n]], [[XP:n]], [[ITEM:nome]], [[DIARIO:testo]].
        Se l'azione richiede competenza, verifica se il PG ce l'ha ({st.session_state.personaggio['competenze']})."""
        
        with st.chat_message("assistant"):
            full_res = model.generate_content(sys_p + "\n" + prompt).text
            
            # Parsing Avanzato
            if "[[LUOGO:" in full_res: genera_img(full_res.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            d_match = re.search(r'\[\[DANNO:(\d+)\]\]', full_res)
            if d_match: st.session_state.hp -= int(d_match.group(1))
            o_match = re.search(r'\[\[ORO:(-?\d+)\]\]', full_res)
            if o_match: st.session_state.oro += int(o_match.group(1))
            x_match = re.search(r'\[\[XP:(\d+)\]\]', full_res)
            if x_match: 
                st.session_state.xp += int(x_match.group(1))
                check_level_up()
            i_match = re.search(r'\[\[ITEM:(.*?)\]\]', full_res)
            if i_match: st.session_state.inventario.append(i_match.group(1).strip())
            
            clean_res = re.sub(r'\[\[.*?\]\]', '', full_res).strip()
            st.markdown(clean_res)
            st.session_state.messages.append({"role": "assistant", "content": clean_res})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
