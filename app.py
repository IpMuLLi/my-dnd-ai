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
        
        # Gestione Galleria
        if "gallery" not in st.session_state:
            st.session_state.gallery = []
        # Evita duplicati in cima
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
    return scelta

def aggiorna_diario(evento):
    """Aggiunge un evento al diario persistente"""
    if "journal" not in st.session_state:
        st.session_state.journal = []
    st.session_state.journal.append(f"- {evento}")
    # Mantiene il diario pulito (ultimi 15 eventi chiave)
    if len(st.session_state.journal) > 15:
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
        "gallery": [], "bestiary": [], "journal": [] 
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

check_level_up()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    
    if st.session_state.personaggio.get("nome"):
        p = st.session_state.personaggio
        aggiorna_ca()
        
        # TAB PRINCIPALI
        tab1, tab2, tab3, tab4 = st.tabs(["Status", "Stats", "Abilità", "Extra"])
        
        with tab1:
            st.subheader(f"{p['nome']} ({p['razza']} {p['classe']})")
            st.metric("Livello", st.session_state.livello, f"XP: {st.session_state.xp}")
            
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

        with tab2:
            st.caption("Caratteristiche & Modificatori")
            for stat, val in p['stats'].items():
                mod = calcola_mod(val)
                segno = "+" if mod >= 0 else ""
                st.text(f"{stat.ljust(12)}: {val} ({segno}{mod})")

        with tab3:
            st.caption(f"Bonus Competenza: +{st.session_state.bonus_competenza}")
            for skill, stat_ref in SKILL_MAP.items():
                is_proficient = skill in p['competenze']
                mod_stat = calcola_mod(p['stats'][stat_ref])
                bonus = mod_stat + (st.session_state.bonus_competenza if is_proficient else 0)
                
                segno = "+" if bonus >= 0 else ""
                prefix = "✅" if is_proficient else "⬜"
                st.text(f"{prefix} {skill.ljust(16)} {segno}{bonus}")

        with tab4:
            if p['magie']:
                st.write("**✨ Grimorio**")
                st.caption(f"Slot: {st.session_state.spell_slots_curr}/{st.session_state.spell_slots_max}")
                for m in p['magie']:
                    st.code(m, language=None)
            
            st.write(f"**💰 Oro:** {st.session_state.oro} mo")
            with st.expander("Zaino"):
                for i in st.session_state.inventario: st.write(f"- {i}")
            if st.button("🎁 Cerca Loot"): genera_loot()

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
                    st.session_state.update({
                        "personaggio": {"nome": n, "classe": c, "razza": r, "stats": st.session_state.temp_stats, "competenze": COMPETENZE_CLASSE[c], "magie": MAGIE_INIZIALI[c]},
                        "hp": hp, "hp_max": hp, "inventario": EQUIP_AVANZATO[c], "game_phase": "playing",
                        "spell_slots_max": 2 if c in ["Mago", "Chierico"] else 0, "spell_slots_curr": 2 if c in ["Mago", "Chierico"] else 0
                    })
                    aggiorna_diario(f"Inizia l'avventura di {n}.")
                    st.session_state.messages.append({"role": "system", "content": "START_INTRO"})
                    st.rerun()

else:
    # --- LAYOUT AVVENTURA ---
    st.title("🛡️ Avventura")
    
    with st.expander("📖 Memorie, Bestiario e Galleria", expanded=False):
        col_mem1, col_mem2, col_mem3 = st.columns(3)
        with col_mem1:
            st.markdown("### 📜 Diario")
            for entry in st.session_state.journal[-5:]:
                st.caption(entry)
        with col_mem2:
            st.markdown("### 👹 Bestiario")
            if st.session_state.bestiary:
                for b in st.session_state.bestiary:
                    st.text(f"{b['nome']} (Max HP: {b['hp_max']})")
            else:
                st.caption("Nessun mostro incontrato.")
        with col_mem3:
            st.markdown("### 🖼️ Galleria")
            if st.session_state.gallery:
                last_img = st.session_state.gallery[0]
                st.image(last_img['url'], caption="Recente", use_container_width=True)
            else:
                st.caption("Nessuna immagine generata.")

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

    # Input Utente e Logica Core
    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        p = st.session_state.personaggio
        journal_str = "\n".join(st.session_state.journal)
        
        # --- LOGICA 5 SCAMBI (MEMORIA CONTESTUALE) ---
        # Prendiamo gli ultimi 10 messaggi (User + AI) escludendo il system
        # Questo permette al DM di ricordare "ho appena detto che c'è un cespuglio"
        msgs_to_include = st.session_state.messages[-11:-1] # Escludiamo l'ultimo appena aggiunto per non duplicarlo nel system
        history_text = ""
        for m in msgs_to_include:
            if m["role"] != "system":
                # Pulizia base per risparmiare token e confusione
                content_clean = re.sub(r'http\S+', '', m["content"]).strip() 
                history_text += f"{m['role'].upper()}: {content_clean}\n"

        # System Prompt con Memoria Iniettata
        sys = (f"Sei il DM (5e). PG: {p['nome']} {p['classe']}. HP:{st.session_state.hp}/{st.session_state.hp_max}. "
               f"Stats: {p['stats']}. Equip: {st.session_state.inventario}. "
               f"Diario Globale: {journal_str}. "
               f"Ultimo Dado Utente: {st.session_state.ultimo_tiro}. "
               f"Nemico Attivo: {st.session_state.nemico_corrente}. "
               f"\n--- STORIA RECENTE (Context) ---\n{history_text}\n"
               f"--- ISTRUZIONI ---\n"
               f"Usa [[NEMICO:nome|hp|ca]] per spawnare, [[DANNO_NEMICO:n]], [[LOOT:rarità]], "
               f"[[DANNO:n]], [[ORO:n]], [[XP:n]]. "
               f"Se cambi scena, metti [[LUOGO:descrizione visiva]] in fondo. "
               f"NON ripetere descrizioni appena date. Reagisci logicamente all'ultima azione.")
        
        try:
            res = model.generate_content(sys + "\n\nAZIONE ATTUALE: " + prompt).text
            
            # --- PARSING E GESTIONE TAG ---
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

            clean_res = re.sub(r'\[\[.*?\]\]', '', res).strip()
            st.session_state.messages.append({"role": "assistant", "content": clean_res, "image_url": img_url})
            st.session_state.ultimo_tiro = None
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore API: {e}")
            
