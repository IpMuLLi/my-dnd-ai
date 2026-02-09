import streamlit as st
import google.generativeai as genai
import random
import json
import urllib.parse
import re

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

# --- 1. FUNZIONI TECNICHE ---
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
    if len(st.session_state.journal) > 20:
        st.session_state.journal.pop(0)

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
    "Guerriero": ["Cotta di Maglia (CA 16)", "Spada Lunga", "Scudo (+2 CA)", "Arco Lungo"],
    "Mago": ["Bastone Arcano", "Libro Incantesimi", "Vesti del Mago", "Daga"],
    "Ladro": ["Daga x2", "Arco Corto", "Armatura di Cuoio (CA 11)", "Arnesi da Scasso"],
    "Ranger": ["Armatura di Cuoio (CA 11)", "Spada Corta x2", "Arco Lungo"],
    "Chierico": ["Mazza", "Scudo (+2 CA)", "Simbolo Sacro", "Cotta di Maglia (CA 16)"]
}

MAGIE_INIZIALI = {
    "Mago": ["Dardo Incantato", "Mano Magica", "Prestidigitazione", "Armatura Magica", "Scudo"],
    "Chierico": ["Guida", "Fiamma Sacra", "Cura Ferite", "Dardo Guida", "Benedizione"],
    "Guerriero": [], "Ladro": [], "Ranger": ["Marchio del Cacciatore"]
}

XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}

# --- 3. STATO ---
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [], "game_phase": "creazione",
        "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}, "competenze": [], "magie": []},
        "hp": 20, "hp_max": 20, "oro": 10, "xp": 0, "livello": 1, "bonus_competenza": 2,
        "inventario": [], "spell_slots_max": 0, "spell_slots_curr": 0,
        "ultimo_tiro": None, "temp_stats": {}, "ca": 10, "event_log": [],
        "nemico_corrente": None,
        "gallery": [], "bestiary": [], "journal": ["- Inizio dell'avventura"] 
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
        aggiorna_diario(f"Level Up! Raggiunto livello {st.session_state.livello}")
        st.toast(f"✨ LIVELLO {st.session_state.livello}!", icon="⚔️")
        
        # Incremento Slot per Mago/Chierico/Ranger al level up
        p_class = st.session_state.personaggio.get("classe", "")
        if p_class in ["Mago", "Chierico"]:
            st.session_state.spell_slots_max = 2 + (st.session_state.livello - 1)
        elif p_class == "Ranger" and st.session_state.livello >= 2:
             st.session_state.spell_slots_max = 2

check_level_up()

# --- 4. SIDEBAR RISTRUTTURATA (CLEAN v2.5) ---
with st.sidebar:
    st.title("🧝 D&D Engine")
    
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        
        # HOTFIX PER RANGER LV1: Diamo 1 slot se non ne ha, per usare Marchio
        if p['classe'] == "Ranger" and st.session_state.spell_slots_max == 0:
            st.session_state.spell_slots_max = 1
            st.session_state.spell_slots_curr = 1

        # TAB PRINCIPALI
        main_tabs = st.tabs(["📊 Eroe", "📚 Diario"])
        
        # --- TAB 1: SCHEDA EROE ---
        with main_tabs[0]:
            st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
            st.caption(f"{p['razza']} {p['classe']} | XP: {st.session_state.xp}")
            
            c1, c2 = st.columns(2)
            c1.metric("❤️ HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
            c2.metric("🛡️ CA", st.session_state.ca)
            
            st.write("---")
            if st.button("🎲 Tira d20 Puro", use_container_width=True): 
                st.session_state.ultimo_tiro = random.randint(1, 20)
            
            c3, c4 = st.columns(2)
            if c3.button("⚔️ Attacco"): 
                stat = "Destrezza" if p['classe'] in ["Ladro", "Ranger"] else "Forza"
                mod = calcola_mod(p['stats'][stat])
                tiro = random.randint(1, 20)
                totale = tiro + mod + st.session_state.bonus_competenza
                st.session_state.ultimo_tiro = f"{totale} (d20:{tiro} + {mod} + {st.session_state.bonus_competenza})"
            
            if c4.button("⛺ Riposo"):
                st.session_state.hp = st.session_state.hp_max
                st.session_state.spell_slots_curr = st.session_state.spell_slots_max
                aggiorna_diario("Riposo Lungo completato. HP e Slot ripristinati.")
                st.toast("Riposo completato!")
            
            if st.session_state.ultimo_tiro:
                st.info(f"Esito: **{st.session_state.ultimo_tiro}**")
            
            # Sotto-Tab Dettagli: ORA SONO 4 per separare Magia e Zaino
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
                        st.rerun()

            with sub_tab3: # TAB MAGIA DEDICATO
                if p['magie']:
                    st.write(f"**Slot:** {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
                    st.progress(st.session_state.spell_slots_curr / max(1, st.session_state.spell_slots_max))
                    for m in p['magie']:
                        st.code(m, language=None)
                else:
                    st.caption("Nessuna capacità magica.")

            with sub_tab4: # TAB ZAINO (Solo oggetti)
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
                    hd = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}
                    hp = hd[c] + mod_c
                    # Assegnazione slot: Ranger parte con 1 slot per fix homebrew
                    start_slots = 2 if c in ["Mago", "Chierico"] else (1 if c == "Ranger" else 0)
                    
                    st.session_state.update({
                        "personaggio": {"nome": n, "classe": c, "razza": r, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[c], "magie": MAGIE_INIZIALI[c]},
                        "hp": hp, "hp_max": hp, "inventario": EQUIP_AVANZATO[c], "game_phase": "playing",
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

    # Input Utente
    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        p = st.session_state.personaggio
        journal_str = "\n".join(st.session_state.journal)
        
        # --- MEMORIA (Context Injection) ---
        msgs_to_include = st.session_state.messages[-11:-1]
        history_text = ""
        for m in msgs_to_include:
            if m["role"] != "system":
                content_clean = re.sub(r'http\S+', '', m["content"]).strip() 
                history_text += f"{m['role'].upper()}: {content_clean}\n"

        # System Prompt
        sys = (f"Sei il DM (5e). PG: {p['nome']} {p['classe']}. HP:{st.session_state.hp}/{st.session_state.hp_max}. "
               f"Stats: {p['stats']}. Equip: {st.session_state.inventario}. "
               f"Diario Globale: {journal_str}. "
               f"Ultimo Dado Utente: {st.session_state.ultimo_tiro}. "
               f"Nemico Attivo: {st.session_state.nemico_corrente}. "
               f"\n--- STORIA RECENTE (Context) ---\n{history_text}\n"
               f"--- ISTRUZIONI ---\n"
               f"Usa [[NEMICO:nome|hp|ca]] per spawnare, [[DANNO_NEMICO:n]], "
               f"[[LOOT:nome_oggetto]], [[DANNO:n]], [[ORO:n]], [[XP:n]]. "
               f"Se cambi scena, metti [[LUOGO:descrizione visiva]] in fondo. "
               f"Reagisci logicamente all'ultima azione.")
        
        try:
            res = model.generate_content(sys + "\n\nAZIONE ATTUALE: " + prompt).text
            
            # --- PARSING ---
            # 1. Nemici
            n_m = re.search(r'\[\[NEMICO:(.*?)\|(.*?)\|(.*?)\]\]', res)
            if n_m: 
                enemy_data = {"nome": n_m.group(1), "hp": int(n_m.group(2)), "hp_max": int(n_m.group(2)), "ca": int(n_m.group(3))}
                st.session_state.nemico_corrente = enemy_data
                aggiorna_diario(f"Apparso nemico: {enemy_data['nome']}")
                if not any(b['nome'] == enemy_data['nome'] for b in st.session_state.bestiary):
                    st.session_state.bestiary.append(enemy_data)

            # 2. Danno Nemico
            dn_m = re.search(r'\[\[DANNO_NEMICO:(\d+)\]\]', res)
            if dn_m and st.session_state.nemico_corrente:
                dmg = int(dn_m.group(1))
                st.session_state.nemico_corrente["hp"] -= dmg
                if st.session_state.nemico_corrente["hp"] <= 0: 
                    aggiorna_diario(f"Sconfitto: {st.session_state.nemico_corrente['nome']}")
                    st.session_state.nemico_corrente = None
            
            # 3. XP/Oro
            xp_m = re.search(r'\[\[XP:(\d+)\]\]', res)
            if xp_m: 
                xp_val = int(xp_m.group(1))
                st.session_state.xp += xp_val
                aggiorna_diario(f"Guadagnati {xp_val} XP")

            o_m = re.search(r'\[\[ORO:(-?\d+)\]\]', res)
            if o_m: st.session_state.oro = max(0, st.session_state.oro + int(o_m.group(1)))
            
            # 4. Danno Giocatore
            d_m = re.search(r'\[\[DANNO:(\d+)\]\]', res)
            if d_m: 
                dmg_pg = int(d_m.group(1))
                st.session_state.hp = max(0, st.session_state.hp - dmg_pg)
                aggiorna_diario(f"Subiti {dmg_pg} danni")

            # 5. Immagini
            img_url = None
            if "[[LUOGO:" in res:
                try:
                    desc_luogo = res.split("[[LUOGO:")[1].split("]]")[0]
                    img_url = genera_img(desc_luogo, "Scene")
                except: pass

            # 6. Loot Automatico
            l_m = re.search(r'\[\[LOOT:(.*?)\]\]', res)
            if l_m:
                genera_loot(l_m.group(1))

            clean_res = re.sub(r'\[\[.*?\]\]', '', res).strip()
            st.session_state.messages.append({"role": "assistant", "content": clean_res, "image_url": img_url})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore API: {e}")
            
