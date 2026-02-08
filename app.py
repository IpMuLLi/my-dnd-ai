import streamlit as st
import google.generativeai as genai
import random
import json
import os

# --- CONFIGURAZIONE CORE ---
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
    prompt_img = f"Dungeons and Dragons style, {tipo}: {descrizione}, high fantasy, detailed, digital art"
    url = f"https://pollinations.ai/p/{prompt_img.replace(' ', '_')}?width=1024&height=1024&seed={seed}&nologo=true"
    img_data = {"url": url, "caption": f"{tipo}: {descrizione[:30]}..."}
    st.session_state.current_image = img_data
    st.session_state.gallery.append(img_data)
    return url

# --- 2. LOGICA DI LIVELLO (XP) ---
# Soglie semplificate D&D 5e: Lv2: 300, Lv3: 900, Lv4: 2700, Lv5: 6500
SOGLIE_XP = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}
DADI_VITA = {"Guerriero": 10, "Mago": 6, "Ladro": 8, "Ranger": 10, "Chierico": 8}

def check_level_up():
    current_lv = st.session_state.livello
    current_xp = st.session_state.xp
    next_lv = current_lv + 1
    
    if next_lv in SOGLIE_XP and current_xp >= SOGLIE_XP[next_lv]:
        st.session_state.livello = next_lv
        # Aumento HP: Dado Vita medio + Modificatore Costituzione
        classe = st.session_state.personaggio["classe"]
        mod_cos = calcola_mod(st.session_state.personaggio["stats"]["Costituzione"])
        guadagno_hp = (DADI_VITA[classe] // 2 + 1) + mod_cos
        
        st.session_state.hp_max += guadagno_hp
        st.session_state.hp = st.session_state.hp_max
        
        # Aumento Slot Incantesimi (se la classe è magica)
        if st.session_state.spell_slots_max > 0:
            st.session_state.spell_slots_max += 1
            st.session_state.spell_slots_curr = st.session_state.spell_slots_max
            
        st.balloons()
        st.success(f"🎊 LEVEL UP! Sei ora di Livello {next_lv}!")
        return True
    return False

# --- 3. GESTIONE SALVATAGGIO ---
SAVE_FILE = "dnd_save_auto.json"

def salva_gioco():
    exclude = ["GEMINI_API_KEY"]
    save_dict = {k: v for k, v in st.session_state.items() if k not in exclude}
    with open(SAVE_FILE, "w") as f:
        json.dump(save_dict, f)

def carica_gioco():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                for k, v in data.items(): st.session_state[k] = v
                return True
        except: return False
    return False

# --- 4. INIZIALIZZAZIONE ---
if "messages" not in st.session_state:
    if not carica_gioco():
        st.session_state.update({
            "messages": [], "game_phase": "creazione",
            "personaggio": {"nome": "", "classe": "", "razza": "", "stats": {}},
            "hp": 20, "hp_max": 20, "oro": 0, "xp": 0, "livello": 1,
            "inventario": [], "missioni": [], "diario": "L'avventura ha inizio...",
            "current_image": None, "gallery": [], "spell_slots_max": 0, "spell_slots_curr": 0,
            "ultimo_tiro": None
        })

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    
    if st.session_state.game_phase != "creazione":
        p = st.session_state.personaggio
        st.subheader(f"{p['nome']} (Lv. {st.session_state.livello})")
        
        # XP Bar
        prossima_soglia = SOGLIE_XP.get(st.session_state.livello + 1, "MAX")
        st.caption(f"Esperienza: {st.session_state.xp} / {prossima_soglia}")
        if prossima_soglia != "MAX":
            progresso_xp = (st.session_state.xp - SOGLIE_XP[st.session_state.livello]) / (prossima_soglia - SOGLIE_XP[st.session_state.livello])
            st.progress(max(0.0, min(1.0, progresso_xp)))

        col1, col2 = st.columns(2)
        col1.metric("HP", f"{st.session_state.hp}/{st.session_state.hp_max}")
        col2.metric("Oro", f"{st.session_state.oro}g")
        st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))
        
        # Statistiche
        s = p['stats']
        cols = st.columns(3)
        for i, (stat, val) in enumerate(s.items()):
            cols[i%3].caption(f"**{stat[:3].upper()}**\n{val}({calcola_mod(val):+})")

        with st.expander("🖼️ Memoria Visiva"):
            for img in reversed(st.session_state.gallery):
                st.image(img["url"], caption=img["caption"])

        if st.button("⛺ Riposo Lungo"):
            st.session_state.hp = st.session_state.hp_max
            st.session_state.spell_slots_curr = st.session_state.spell_slots_max
            st.success("Salute e Slot ripristinati!")
            salva_gioco()

    if st.button("🗑️ Reset Avventura"):
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
        st.session_state.clear()
        st.rerun()

# --- 6. LOGICA DI GIOCO ---
st.title("⚔️ D&D Legend Engine 2026")

if st.session_state.game_phase == "creazione":
    with st.form("char_creation"):
        nome = st.text_input("Nome dell'Eroe")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling", "Mezzelfo"])
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Ranger", "Chierico"])
        if st.form_submit_button("Inizia") and nome:
            setup = {"Guerriero": (12,0,["Spada"]), "Mago": (6,3,["Bastone"]), "Ladro": (8,0,["Pugnali"]), "Ranger": (10,2,["Arco"]), "Chierico": (8,3,["Mazza"])}
            hp_b, slots, inv = setup[classe]
            stats = {k: tira_statistica() for k in ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]}
            st.session_state.update({
                "personaggio": {"nome": nome, "classe": classe, "razza": razza, "stats": stats},
                "hp_max": hp_b + calcola_mod(stats["Costituzione"]), "hp": hp_b + calcola_mod(stats["Costituzione"]),
                "inventario": inv, "spell_slots_max": slots, "spell_slots_curr": slots, "game_phase": "playing", "xp": 0, "livello": 1
            })
            res = model.generate_content(f"DM. Introduci l'avventura per {nome}, {razza} {classe}. Usa [[LUOGO:ambientazione]].").text
            if "[[LUOGO:" in res: genera_img(res.split("[[LUOGO:")[1].split("]]")[0], "Luogo")
            st.session_state.messages.append({"role": "assistant", "content": res})
            salva_gioco()
            st.rerun()
else:
    if st.session_state.current_image:
        st.image(st.session_state.current_image["url"], use_container_width=True)
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sys_p = f"""Sei un DM di D&D 5e. Personaggio: {st.session_state.personaggio}. HP: {st.session_state.hp}.
        Tag obbligatori per modifiche stato:
        - [[LUOGO:desc]], [[MOSTRO:desc]], [[OGGETTO:desc]]
        - [[DANNO:n]] (positivo=danno, negativo=cura)
        - [[ORO:n]], [[XP:n]] (per ricompense)
        - [[DIARIO:riassunto]]
        Usa il dado {st.session_state.ultimo_tiro} se presente."""

        with st.chat_message("assistant"):
            full_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
            response = model.generate_content(sys_p + "\n" + full_history).text
            
            # Parsing Tag
            tags = {"[[LUOGO:": "Luogo", "[[MOSTRO:": "Mostro", "[[OGGETTO:": "Oggetto"}
            for tag, label in tags.items():
                if tag in response: genera_img(response.split(tag)[1].split("]]")[0], label)
            
            if "[[DANNO:" in response: st.session_state.hp = max(0, min(st.session_state.hp_max, st.session_state.hp - int(response.split("[[DANNO:")[1].split("]]")[0])))
            if "[[ORO:" in response: st.session_state.oro += int(response.split("[[ORO:")[1].split("]]")[0])
            if "[[XP:" in response: 
                st.session_state.xp += int(response.split("[[XP:")[1].split("]]")[0])
                check_level_up()
            if "[[DIARIO:" in response: st.session_state.diario = response.split("[[DIARIO:")[1].split("]]")[0]
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.ultimo_tiro = None
            salva_gioco()
            st.rerun()
        
