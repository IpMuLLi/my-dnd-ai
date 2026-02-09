import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re
import time

# --- CONFIGURAZIONE CORE ---
st.set_page_config(page_title="D&D Legend Engine 2026", layout="wide", initial_sidebar_state="expanded")

# Configurazione API Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Configura GEMINI_API_KEY nei Secrets!")

# Recupero chiave Pollinations (Opzionale)
POLL_KEY = st.secrets.get("POLLINATIONS_API_KEY", None)

# CORE MODEL: Gemini 2.5 Flash Lite
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 1. FUNZIONI TECNICHE (PRESERVATE & ESTESE) ---
def tira_dado(formula):
    """Parsa stringhe come '1d8+2' o '2d6' e restituisce il risultato."""
    try:
        formula = formula.lower().replace(" ", "")
        bonus = 0
        if "+" in formula:
            parts = formula.split("+")
            formula = parts[0]
            bonus = int(parts[1])
        elif "-" in formula:
            parts = formula.split("-")
            formula = parts[0]
            bonus = -int(parts[1])
            
        if "d" in formula:
            num, faces = map(int, formula.split("d"))
            tiri = [random.randint(1, faces) for _ in range(num)]
            return sum(tiri) + bonus, tiri
        else:
            return int(formula), []
    except:
        return 0, []

def tira_statistica():
    dadi = [random.randint(1, 6) for _ in range(4)]
    dadi.sort()
    return sum(dadi[1:])

def calcola_mod(punteggio):
    return (punteggio - 10) // 2

def genera_img(descrizione, tipo):
    try:
        seed = random.randint(1, 99999)
        # Prompt ottimizzato per il modello Flux
        prompt_base = f"Dungeons and Dragons realistic high fantasy, {tipo}: {descrizione}, cinematic lighting, 8k, masterpiece, no text"
        prompt_encoded = urllib.parse.quote(prompt_base)
        
        # Endpoint 2026
        base_url = f"https://gen.pollinations.ai/image/{prompt_encoded}"
        
        params = [
            "width=1024",
            "height=1024",
            f"seed={seed}",
            "nologo=true",
            "model=flux" 
        ]
        
        if POLL_KEY:
            params.append(f"key={POLL_KEY}")
            
        url = f"{base_url}?{'&'.join(params)}"
        
        # Gestione Galleria (Memoria)
        if "gallery" not in st.session_state:
            st.session_state.gallery = []
        if not st.session_state.gallery or st.session_state.gallery[0]['url'] != url:
            st.session_state.gallery.insert(0, {"url": url, "desc": descrizione})
        
        return url
    except: return None

def genera_loot(rarita="Comune"):
    tabella = {
        "Comune": ["Pozione di Guarigione", "Pergamena di Dardo Incantato", "Olio per Affilare", "Torcia", "Razioni", "Corda di Seta"],
        "Non Comune": ["Spada +1", "Anello di Protezione", "Mantello del Saltimpalo", "Borsa Conservante", "Stivali Alati"],
        "Raro": ["Armatura di Piastre +1", "Bacchetta delle Palle di Fuoco", "Pozione di Forza del Gigante"]
    }
    scelta = random.choice(tabella.get(rarita, tabella["Comune"]))
    if scelta not in st.session_state.inventario:
        st.session_state.inventario.append(scelta)
        aggiorna_diario(f"Trovato oggetto: {scelta} ({rarita})")
        st.toast(f"Trovato: {scelta}", icon="🎁")
    return scelta

def aggiorna_diario(evento):
    """Aggiunge un evento al diario persistente"""
    if "journal" not in st.session_state:
        st.session_state.journal = []
    st.session_state.journal.append(f"- {evento}")
    if len(st.session_state.journal) > 50: # Aumentato buffer per la memoria progressiva
        st.session_state.journal.pop(0)

def gestisci_memoria():
    """Compime la storia se troppo lunga (Progressive Summary)"""
    if len(st.session_state.messages) > 15:
        st.toast("🧠 Consolidamento memoria...", icon="💾")
        try:
            old_msgs = st.session_state.messages[1:-5] # Mantieni intro e ultimi 5
            txt_to_sum = "\n".join([f"{m['role']}: {m['content']}" for m in old_msgs if m['role'] != 'system'])
            
            summary_prompt = f"Riassumi i seguenti eventi di D&D in 3 frasi concise mantenendo nomi e fatti chiave:\n{txt_to_sum}"
            summary = model.generate_content(summary_prompt).text
            
            st.session_state.summary_history += f"\n{summary}"
            # Mantieni solo system, il summary aggiornato (virtualmente) e gli ultimi messaggi
            st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-5:]
        except Exception as e:
            print(f"Errore memoria: {e}")

# --- 2. DATASETS ORIGINALI ---
SKILL_MAP = {
    "Atletica": "Forza", "Furtività": "Destrezza", "Rapidità di mano": "Destrezza", "Acrobazia": "Destrezza",
    "Arcano": "Intelligenza", "Storia": "Intelligenza", "Indagare": "Intelligenza", "Natura": "Intelligenza", "Religione": "Intelligenza",
    "Percezione": "Saggezza", "Intuizione": "Saggezza", "Sopravvivenza": "Saggezza", "Medicina": "Saggezza", "Addestrare Animali": "Saggezza",
    "Persuasione": "Carisma", "Inganno": "Carisma", "Intimidire": "Carisma", "Intrattenere": "Carisma"
}

COMPETENZE_CLASSE = {
    "Guerriero": ["Atletica", "Percezione", "Intimidire"],
    "Mago": ["Arcano", "Storia", "Indagare"],
    "Ladro": ["Furtività", "Rapidità di mano", "Indagare", "Inganno"],
    "Ranger": ["Sopravvivenza", "Percezione", "Natura"],
    "Chierico": ["Religione", "Intuizione", "Storia"]
}

EQUIP_AVANZATO = {
    "Guerriero": ["Cotta di Maglia (CA 16)", "Spada Lunga (1d8)", "Scudo (+2 CA)", "Arco Lungo (1d8)"],
    "Mago": ["Bastone Arcano (1d6)", "Libro Incantesimi", "Vesti del Mago", "Daga (1d4)"],
    "Ladro": ["Daga (1d4) x2", "Arco Corto (1d6)", "Armatura di Cuoio (CA 11)", "Arnesi da Scasso"],
    "Ranger": ["Armatura di Cuoio (CA 11)", "Spada Corta (1d6) x2", "Arco Lungo (1d8)"],
    "Chierico": ["Mazza (1d6)", "Scudo (+2 CA)", "Simbolo Sacro", "Cotta di Maglia (CA 16)"]
}

MAGIE_INIZIALI = {
    "Mago": ["Dardo Incantato", "Mano Magica", "Raggio di Gelo", "Armatura Magica", "Scudo"],
    "Chierico": ["Guida", "Fiamma Sacra", "Cura Ferite", "Dardo Guida", "Benedizione"],
    "Guerriero": [], "Ladro": [], "Ranger": ["Marchio del Cacciatore"]
}

# Mapping Dadi Vita per classe (NUOVO)
HIT_DICE_MAP = {
    "Guerriero": 10, "Ranger": 10, 
    "Ladro": 8, "Chierico": 8, 
    "Mago": 6
}

XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}

# --- 3. STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": [], "magie": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "hit_dice_max": 1, "hit_dice_curr": 1, # NUOVO: Dadi Vita
        "ultimo_tiro": None, "temp_stats": {}, "ca": 10, "event_log": [],
        "nemico_corrente": None,
        "gallery": [], "bestiary": [], "journal": ["- Inizio dell'avventura"],
        "summary_history": "", # NUOVO: Memoria a lungo termine
        "pending_action": None # NUOVO: Coda azioni UI -> Chat
    })

def aggiorna_ca():
    stats = st.session_state.personaggio.get('stats', {})
    mod_des = calcola_mod(stats.get('Destrezza', 10))
    inv = st.session_state.inventario
    ca_finale = 10 + mod_des
    if any("Cotta di Maglia" in item for item in inv): ca_finale = 16
    elif any("Armatura di Cuoio" in item for item in inv): ca_finale = 11 + mod_des
    if any("Scudo" in item for item in inv): ca_finale += 2
    st.session_state.ca = ca_finale

def check_level_up():
    prossimo_liv = XP_LEVELS.get(st.session_state.livello + 1, 999999)
    if st.session_state.xp >= prossimo_liv:
        st.session_state.livello += 1
        st.session_state.bonus_competenza = 2 + ((st.session_state.livello - 1) // 4)
        st.session_state.hit_dice_max = st.session_state.livello # Aggiorna max Dadi Vita
        st.session_state.hit_dice_curr += 1
        aggiorna_diario(f"Level Up! Raggiunto livello {st.session_state.livello}")
        st.toast(f"✨ LIVELLO {st.session_state.livello}!", icon="⚔️")
        
        p_class = st.session_state.personaggio.get("classe", "")
        if p_class in ["Mago", "Chierico"]:
            st.session_state.spell_slots_max = 2 + (st.session_state.livello - 1)
        elif p_class == "Ranger" and st.session_state.livello >= 2:
             st.session_state.spell_slots_max = 2

check_level_up()
# --- 4. SIDEBAR RISTRUTTURATA (UI MIGLIORATA) ---
with st.sidebar:
    st.title("🧝 D&D Engine")
    
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        
        # HOTFIX PER RANGER LV1
        if p['classe'] == "Ranger" and st.session_state.spell_slots_max == 0:
            st.session_state.spell_slots_max = 1
            st.session_state.spell_slots_curr = 1

        # TAB PRINCIPALI
        main_tabs = st.tabs(["📊 Eroe", "📚 Diario"])
        
        # --- TAB 1: SCHEDA EROE ---
        with main_tabs[0]:
            st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
            st.caption(f"{p['razza']} {p['classe']} | XP: {st.session_state.xp}")
            
            # --- UI VISIVA HP ---
            hp_pct = st.session_state.hp / st.session_state.hp_max
            col_hp_val = "green" if hp_pct > 0.5 else ("orange" if hp_pct > 0.2 else "red")
            st.write(f"**HP: {st.session_state.hp}/{st.session_state.hp_max}**")
            st.progress(hp_pct)
            
            c_ca, c_hd = st.columns(2)
            c_ca.metric("🛡️ CA", st.session_state.ca)
            c_hd.metric("🎲 Dadi Vita", f"{st.session_state.hit_dice_curr}/{st.session_state.hit_dice_max}")

            st.write("---")
            if st.button("🎲 Tira d20 Puro", use_container_width=True): 
                res = random.randint(1, 20)
                st.session_state.ultimo_tiro = res
                st.session_state.pending_action = f"[DADO PURO: {res}]"
            
            # SEZIONE COMBATTIMENTO/RIPOSO MIGLIORATA
            c1, c2 = st.columns(2)
            
            # MENU SELEZIONE ARMA (Nuova Implementazione)
            with c1:
                # 1. Trova armi nell'inventario
                weapons_found = []
                for item in st.session_state.inventario:
                    # Logica base per identificare armi e stat associata
                    if any(x in item for x in ["Spada", "Mazza", "Ascia", "Martello", "Bastone"]):
                         dice = "1d8" if "Lunga" in item or "Ascia" in item else ("1d4" if "Daga" in item else "1d6")
                         weapons_found.append({"label": item, "stat": "Forza", "dice": dice})
                    elif any(x in item for x in ["Arco", "Daga", "Balestra", "Fionda"]):
                         dice = "1d8" if "Lungo" in item or "Balestra" in item else ("1d4" if "Daga" in item else "1d6")
                         weapons_found.append({"label": item, "stat": "Destrezza", "dice": dice})
                
                # Fallback Pugno
                if not weapons_found:
                    weapons_found.append({"label": "Pugno", "stat": "Forza", "dice": "1d4"})
                
                # 2. Selectbox per scegliere l'arma
                selected_weapon = st.selectbox("Scegli Arma", weapons_found, format_func=lambda x: x["label"].split('(')[0], label_visibility="collapsed")
                
                # 3. Tasto Attacco Dinamico
                if st.button(f"⚔️ Usa {selected_weapon['label'].split('(')[0]}"):
                    mod = calcola_mod(p['stats'][selected_weapon['stat']])
                    tiro_atk = random.randint(1, 20)
                    tot_atk = tiro_atk + mod + st.session_state.bonus_competenza
                    
                    danno, _ = tira_dado(selected_weapon['dice'])
                    danno_tot = max(1, danno + mod)
                    
                    # Genera Azione Strutturata per LLM
                    action_str = (f"[AZIONE_COMBAT: Attacco con {selected_weapon['label'].split('(')[0]} ({selected_weapon['stat']}) | "
                                  f"TxC: {tot_atk} (d20:{tiro_atk}+{mod}+prof) | "
                                  f"Danni: {danno_tot} ({selected_weapon['dice']}+{mod})]")
                    st.session_state.pending_action = action_str
                    st.session_state.ultimo_tiro = f"Atk: {tot_atk} | Dmg: {danno_tot}"

            # Menu Riposo (Short/Long)
            with c2:
                rest_type = st.selectbox("Riposo", ["Breve (1 HD)", "Lungo"], label_visibility="collapsed")
                if st.button("💤 Dormi"):
                    if "Lungo" in rest_type:
                        st.session_state.hp = st.session_state.hp_max
                        st.session_state.spell_slots_curr = st.session_state.spell_slots_max
                        st.session_state.hit_dice_curr = max(1, st.session_state.hit_dice_max // 2)
                        aggiorna_diario("Riposo Lungo completato.")
                        st.session_state.pending_action = "[AZIONE: Riposo Lungo completato]"
                    else: # Riposo Breve
                        if st.session_state.hit_dice_curr > 0:
                            dice_face = HIT_DICE_MAP.get(p['classe'], 8)
                            roll = random.randint(1, dice_face)
                            con_mod = calcola_mod(p['stats']['Costituzione'])
                            heal = max(1, roll + con_mod)
                            
                            st.session_state.hp = min(st.session_state.hp_max, st.session_state.hp + heal)
                            st.session_state.hit_dice_curr -= 1
                            
                            aggiorna_diario(f"Riposo Breve: Curati {heal} HP")
                            st.session_state.pending_action = f"[AZIONE: Riposo Breve. Speso 1 Dado Vita. Curati {heal} HP.]"
                            st.toast(f"Curati {heal} HP")
                        else:
                            st.error("Nessun Dado Vita rimasto!")

            if st.session_state.ultimo_tiro:
                st.info(f"Esito: **{st.session_state.ultimo_tiro}**")
            
            # Sotto-Tab Dettagli
            sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["Stats", "Abilità", "Magia", "Zaino"])
            
            with sub_tab1:
                for stat, val in p['stats'].items():
                    mod = calcola_mod(val)
                    segno = "+" if mod >= 0 else ""
                    st.text(f"{stat[:3].upper()}: {val} ({segno}{mod})")

            with sub_tab2:
                st.caption("Clicca per tirare:")
                for skill, stat_ref in SKILL_MAP.items():
                    is_proficient = skill in p['competenze']
                    mod_stat = calcola_mod(p['stats'][stat_ref])
                    bonus = mod_stat + (st.session_state.bonus_competenza if is_proficient else 0)
                    segno = "+" if bonus >= 0 else ""
                    prefix = "✅" if is_proficient else "⬜"
                    
                    sk_col1, sk_col2 = st.columns([3, 1])
                    sk_col1.markdown(f"**{skill}** ({prefix})")
                    if sk_col2.button(f"{segno}{bonus}", key=f"btn_{skill}"):
                        dado = random.randint(1, 20)
                        totale = dado + bonus
                        st.session_state.ultimo_tiro = f"{totale} ({skill}: {dado} {segno} {bonus})"
                        st.session_state.pending_action = f"[PROVA_ABILITA: {skill} | Totale: {totale}]"

            with sub_tab3: # TAB MAGIA ATTIVO
                if p['magie']:
                    st.write(f"**Slot:** {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
                    st.progress(st.session_state.spell_slots_curr / max(1, st.session_state.spell_slots_max))
                    
                    for m in p['magie']:
                        c_m1, c_m2 = st.columns([3, 1])
                        c_m1.code(m, language=None)
                        if c_m2.button("✨", key=f"cast_{m}"):
                            # Logica Semplificata Casting
                            if st.session_state.spell_slots_curr > 0 or m in ["Guida", "Fiamma Sacra", "Raggio di Gelo", "Mano Magica", "Prestidigitazione"]: # Cantrips check molto base
                                is_cantrip = m in ["Guida", "Fiamma Sacra", "Raggio di Gelo", "Mano Magica", "Prestidigitazione"]
                                if not is_cantrip:
                                    st.session_state.spell_slots_curr -= 1
                                
                                # Esempio Danni comuni
                                dmg_roll = ""
                                if m == "Dardo Incantato": dmg_roll = f"Danni: {sum([random.randint(1,4)+1 for _ in range(3)])} (Forza)"
                                elif m == "Cura Ferite": 
                                    heal = random.randint(1,8) + calcola_mod(p['stats'].get('Saggezza', 10))
                                    dmg_roll = f"Cura: {heal} HP"
                                    st.session_state.hp = min(st.session_state.hp_max, st.session_state.hp + heal)
                                
                                st.session_state.pending_action = f"[LANCIO_INCANTESIMO: {m} | {dmg_roll} | Slot Rimanenti: {st.session_state.spell_slots_curr}]"
                            else:
                                st.error("Slot esauriti!")
                else:
                    st.caption("Nessuna capacità magica.")

            with sub_tab4: 
                st.write(f"**💰 Oro:** {st.session_state.oro} mo")
                if not st.session_state.inventario:
                    st.caption("Zaino vuoto.")
                for i in st.session_state.inventario: 
                    st.write(f"- {i}")

        # --- TAB 2: DIARIO ---
        with main_tabs[1]:
            st.write("### 📜 Diario Avventura")
            if st.session_state.journal:
                for entry in reversed(st.session_state.journal):
                    st.caption(entry)
            else:
                st.caption("Il diario è ancora intonso.")
            
            st.divider()
            
            st.write("### 👹 Bestiario")
            if st.session_state.bestiary:
                for b in st.session_state.bestiary:
                    st.error(f"**{b['nome']}** (HP Max: {b['hp_max']})")
            else:
                st.caption("Nessuna creatura registrata.")

        st.divider()
        sd = {k: v for k, v in st.session_state.items() if k != "temp_stats"}
        st.download_button("💾 Salva Eroe", data=json.dumps(sd), file_name="hero.json")

# --- 5. LOGICA DI GIOCO ---
if st.session_state.game_phase == "creazione":
    st.title("🧙 Legend Engine 2026")
    
    with st.expander("📂 Carica Personaggio"):
        f = st.file_uploader("Upload .json", type="json")
        if f:
            st.session_state.update(json.load(f))
            st.rerun()

    if not st.session_state.temp_stats:
        if st.button("🎲 Genera Statistiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()
    else:
        st.write("### Risultati dadi")
        cs = st.columns(6)
        for i, (s, v) in enumerate(st.session_state.temp_stats.items()):
            mod = calcola_mod(v)
            cs[i].metric(s, f"{v}", f"{'+' if mod >=0 else ''}{mod}")
        
        if st.button("🔄 Reroll Caratteristiche"):
            st.session_state.temp_stats = {s: tira_statistica() for s in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.rerun()

        with st.form("f_crea"):
            n = st.text_input("Nome")
            r = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
            c = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
            if st.form_submit_button("Inizia Avventura"):
                if n:
                    mod_c = calcola_mod(st.session_state.temp_stats["Costituzione"])
                    hd = HIT_DICE_MAP.get(c, 8)
                    hp = hd + mod_c
                    start_slots = 2 if c in ["Mago", "Chierico"] else (1 if c == "Ranger" else 0)
                    
                    st.session_state.update({
                        "personaggio": {"nome": n, "classe": c, "razza": r, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[c], "magie": MAGIE_INIZIALI[c]},
                        "hp": hp, "hp_max": hp, 
                        "hit_dice_max": 1, "hit_dice_curr": 1,
                        "inventario": EQUIP_AVANZATO[c], "game_phase": "playing",
                        "spell_slots_max": start_slots, "spell_slots_curr": start_slots
                    })
                    aggiorna_diario(f"Inizia l'avventura di {n}.")
                    st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                    st.rerun()

else:
    # --- LAYOUT AVVENTURA ---
    st.title("🛡️ Avventura")

    # Intro Logic
    if st.session_state.messages and st.session_state.messages[-1]["content"] == "START_INTRO":
        p = st.session_state.personaggio
        res = model.generate_content(
            f"DM. Inizia avventura per {p['nome']} un {p['razza']} {p['classe']}. "
            f"Descrivi l'ambiente in modo evocativo (max 80 parole). "
            f"Usa [[LUOGO:descrizione visiva]] *alla fine* del messaggio."
        ).text
        
        img_url = None
        if "[[LUOGO:" in res:
            try:
                desc_luogo = res.split("[[LUOGO:")[1].split("]]")[0]
                img_url = genera_img(desc_luogo, "Environment")
            except: pass
            
        st.session_state.messages[-1] = {"role": "assistant", "content": re.sub(r'\[\[.*?\]\]', '', res).strip(), "image_url": img_url}
        st.rerun()

    # Render Chat
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("image_url"): st.image(msg["image_url"])

    # Gestione Memoria Progressiva
    gestisci_memoria()

    # Input Logic Combinata (Chat O Azione UI)
    prompt = st.chat_input("Cosa fai?")
    
    # Se c'è un'azione pendente dai bottoni o un input chat
    input_to_process = None
    if st.session_state.pending_action:
        input_to_process = st.session_state.pending_action
        st.session_state.pending_action = None # Reset immediato
    elif prompt:
        input_to_process = prompt

    if input_to_process:
        # Mostra messaggio utente (se non è un comando di sistema interno nascosto, ma qui mostriamo tutto per chiarezza)
        display_text = input_to_process.replace("[AZIONE_COMBAT:", "⚔️ Attacco:").replace("[LANCIO_INCANTESIMO:", "✨ Cast:").replace("]", "")
        st.session_state.messages.append({"role": "user", "content": display_text})
        
        p = st.session_state.personaggio
        journal_str = "\n".join(st.session_state.journal[-10:])
        
        # --- Context Injection ---
        msgs_to_include = st.session_state.messages[-6:] # Short Context
        history_text = st.session_state.summary_history + "\n" # Long Context
        for m in msgs_to_include:
            if m["role"] != "system":
                content_clean = re.sub(r'http\S+', '', m["content"]).strip() 
                history_text += f"{m['role'].upper()}: {content_clean}\n"

        # Initiative Hint per LLM
        combat_hint = ""
        if st.session_state.nemico_corrente:
            dex_pg = calcola_mod(p['stats']['Destrezza'])
            combat_hint = f"\nCOMBATTIMENTO ATTIVO vs {st.session_state.nemico_corrente['nome']}. Il giocatore ha iniziativa +{dex_pg}."

        # System Prompt Potenziato
        sys = (f"Sei il DM (5e). PG: {p['nome']} {p['classe']}. HP:{st.session_state.hp}/{st.session_state.hp_max}. "
               f"Stats: {p['stats']}. Equip: {st.session_state.inventario}. "
               f"Diario Recente: {journal_str}. "
               f"Nemico Attivo: {st.session_state.nemico_corrente}. {combat_hint}"
               f"\n--- STORIA (Context) ---\n{history_text}\n"
               f"--- ISTRUZIONI TECNICHE ---\n"
               f"1. Parsing Robusto: Usa SEMPRE questi tag per le modifiche di stato.\n"
               f"   - [[NEMICO: Nome | HP | CA]] (Es: [[NEMICO:Goblin|7|15]])\n"
               f"   - [[DANNO_NEMICO: n]] (Se il giocatore colpisce)\n"
               f"   - [[DANNO: n]] (Se il nemico colpisce il giocatore)\n"
               f"   - [[ORO: n]], [[XP: n]], [[LOOT: nome]]\n"
               f"   - [[LUOGO: descrizione]] (Solo se cambia scena)\n"
               f"2. Se l'input contiene [AZIONE_COMBAT] o [LANCIO_INCANTESIMO], usa i numeri forniti per narrare l'esito (non ritirare i dadi).\n"
               f"3. Narrazione breve e incalzante.")
        
        try:
            # Generazione
            full_prompt = sys + "\n\nAZIONE: " + input_to_process
            res = model.generate_content(full_prompt).text
            
            # --- PARSING ROBUSTO (REGEX MIGLIORATA) ---
            
            # 1. Nemici (Gestisce spazi extra)
            n_m = re.search(r'\[\[NEMICO:\s*(.*?)\|\s*(\d+)\|\s*(\d+)\]\]', res)
            if n_m: 
                enemy_data = {"nome": n_m.group(1).strip(), "hp": int(n_m.group(2)), "hp_max": int(n_m.group(2)), "ca": int(n_m.group(3))}
                st.session_state.nemico_corrente = enemy_data
                aggiorna_diario(f"Ingaggio: {enemy_data['nome']}")
                if not any(b['nome'] == enemy_data['nome'] for b in st.session_state.bestiary):
                    st.session_state.bestiary.append(enemy_data)

            # 2. Danno Nemico
            dn_m = re.search(r'\[\[DANNO_NEMICO:\s*(\d+)\]\]', res)
            if dn_m and st.session_state.nemico_corrente:
                dmg = int(dn_m.group(1))
                st.session_state.nemico_corrente["hp"] -= dmg
                if st.session_state.nemico_corrente["hp"] <= 0: 
                    aggiorna_diario(f"Sconfitto: {st.session_state.nemico_corrente['nome']}")
                    st.session_state.nemico_corrente = None
                    st.toast("Nemico sconfitto!", icon="💀")
            
            # 3. XP/Oro
            xp_m = re.search(r'\[\[XP:\s*(\d+)\]\]', res)
            if xp_m: 
                xp_val = int(xp_m.group(1))
                st.session_state.xp += xp_val
                aggiorna_diario(f"+{xp_val} XP")

            o_m = re.search(r'\[\[ORO:\s*(-?\d+)\]\]', res)
            if o_m: st.session_state.oro = max(0, st.session_state.oro + int(o_m.group(1)))
            
            # 4. Danno Giocatore
            d_m = re.search(r'\[\[DANNO:\s*(\d+)\]\]', res)
            if d_m: 
                dmg_pg = int(d_m.group(1))
                st.session_state.hp = max(0, st.session_state.hp - dmg_pg)
                aggiorna_diario(f"Subiti {dmg_pg} danni")
                st.toast(f"-{dmg_pg} HP", icon="🩸")

            # 5. Immagini
            img_url = None
            if "[[LUOGO:" in res:
                try:
                    desc_luogo = res.split("[[LUOGO:")[1].split("]]")[0]
                    img_url = genera_img(desc_luogo, "Scene")
                except: pass

            # 6. Loot Automatico
            l_m = re.search(r'\[\[LOOT:\s*(.*?)\]\]', res)
            if l_m:
                genera_loot(l_m.group(1))

            clean_res = re.sub(r'\[\[.*?\]\]', '', res).strip()
            st.session_state.messages.append({"role": "assistant", "content": clean_res, "image_url": img_url})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore API: {e}")
            
