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

# Modello Gemini 2.5 Flash (Target 2026)
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

# --- 2. LOGICA XP, LIVELLO & ABILITÀ (PRESERVATA) ---
SOGLIE_XP = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}
DADI_VITA = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}

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
                if skill in SKILL_MAP:
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

        save_data = json.dumps({k: v for k, v in st.session_state.items() if k != "GEMINI_API_KEY"}, indent=4)
        st.download_button("💾 Esporta Salvataggio", save_data, file_name=f"sav_{st.session_state.personaggio['nome']}.json", use_container_width=True)

        if st.button("🗑️ Reset"):
            st.session_state.clear()
            st.rerun()

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🎲 Creazione Personaggio")
    
    with st.expander("📂 Carica Personaggio Esistente"):
        up_file = st.file_uploader("Carica file .json", type="json")
        if up_file:
            try:
                data = json.load(up_file)
                for k, v in data.items():
                    st.session_state[k] = v
                st.success("Salvataggio caricato con successo!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore nel caricamento: {e}")
    
    st.divider()

    if not st.session_state.temp_stats:
        if st.button("🎲 Lancia Caratteristiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        cols = st.columns(3)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            cols[i%3].metric(s, v)
        
        # FIX REROLL: Aggiorna senza svuotare per non tornare indietro
        if st.button("🔄 Reroll"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()

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
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"[[INTRODUZIONE]] Benvenuto, {nome}. La tua storia ha inizio..."
                })
                st.rerun()

else:
    st.title("⚔️ D&D Legend Engine 2026")
    
    # Area Tiri
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

    # Visualizzazione Messaggi (con immagini integrate nella chat)
    for msg in st.session_state.messages:
        if "[[INTRODUZIONE]]" not in msg["content"]:
            with st.chat_message(msg["role"]):
                # Se il messaggio contiene un'immagine associata (salvata in gallery)
                st.markdown(msg["content"])
                if "image_url" in msg:
                    st.image(msg["image_url"], use_container_width=True)

    # Trigger Introduzione
    if len(st.session_state.messages) == 1 and "[[INTRODUZIONE]]" in st.session_state.messages[0]["content"]:
        with st.chat_message("assistant"):
            intro_prompt = f"Sei il DM. Introduci l'avventura per {st.session_state.personaggio['nome']}, {st.session_state.personaggio['razza']} {st.session_state.personaggio['classe']}. Equipaggiamento: {st.session_state.inventario}. Usa [[LUOGO:descrizione]]."
            response = model.generate_content(intro_prompt).text
            img_url = None
            if "[[LUOGO:" in response:
                loc = response.split("[[LUOGO:")[1].split("]]")[0]
                img_url = genera_img(loc, "Scenario Iniziale")
            clean_intro = re.sub(r'\[\[.*?\]\]', '', response).strip()
            st.markdown(clean_intro)
            if img_url: st.image(img_url, use_container_width=True)
            
            # Salviamo l'URL nell'oggetto messaggio per la persistenza
            st.session_state.messages[0]["content"] = clean_intro
            if img_url: st.session_state.messages[0]["image_url"] = img_url
            st.rerun()

    # Chat Input & DM Engine
    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_p = f"""DM 5e. PG: {st.session_state.personaggio}. LV: {st.session_state.livello}. 
        Tiro: {st.session_state.ultimo_tiro if st.session_state.ultimo_tiro else 'Nessuno'}.
        Tag obbligatori: [[LUOGO:desc]], [[DANNO:n]], [[ORO:n]], [[XP:n]], [[ITEM:nome]], [[DIARIO:testo]]."""
        
        with st.chat_message("assistant"):
            full_res = model.generate_content(sys_p + "\n" + prompt).text
            img_url = None
            
            # Parsing dei Tag
            if "[[LUOGO:" in full_res: 
                loc = full_res.split("[[LUOGO:")[1].split("]]")[0]
                img_url = genera_img(loc, "Luogo")
            
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
            
            if "[[DIARIO:" in full_res: 
                st.session_state.diario += "\n- " + full_res.split("[[DIARIO:")[1].split("]]")[0]
            
            clean_res = re.sub(r'\[\[.*?\]\]', '', full_res).strip()
            st.markdown(clean_res)
            if img_url: st.image(img_url, use_container_width=True)
            
            # Aggiunta al log con immagine per persistenza
            new_msg = {"role": "assistant", "content": clean_res}
            if img_url: new_msg["image_url"] = img_url
            st.session_state.messages.append(new_msg)
            
            st.session_state.ultimo_tiro = None
            st.rerun()
            
