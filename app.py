import streamlit as st
import google.generativeai as genai
import random

# --- CONFIGURAZIONE CORE 2026 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- INIZIALIZZAZIONE STATO ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "game_phase" not in st.session_state:
    st.session_state.game_phase = "creazione"
if "personaggio" not in st.session_state:
    st.session_state.personaggio = {"nome": "", "classe": "", "razza": ""}
if "hp_max" not in st.session_state:
    st.session_state.hp_max = 20
if "hp" not in st.session_state:
    st.session_state.hp = 20
if "livello" not in st.session_state:
    st.session_state.livello = 1
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "oro" not in st.session_state:
    st.session_state.oro = 50
if "inventario" not in st.session_state:
    st.session_state.inventario = ["Razioni", "Acciarino"]
if "ultimo_tiro" not in st.session_state:
    st.session_state.ultimo_tiro = None

# --- FUNZIONI ---
def controlla_livello():
    soglia = st.session_state.livello * 100
    if st.session_state.xp >= soglia:
        st.session_state.livello += 1
        st.session_state.xp -= soglia
        st.session_state.hp_max += 10
        st.session_state.hp = st.session_state.hp_max
        st.toast(f"✨ LEVEL UP! Livello {st.session_state.livello}!", icon="⚔️")

def genera_immagine(descrizione):
    st.image(f"https://placehold.co/600x400?text={descrizione.replace(' ', '+')}", caption="Visuale dell'Eroe")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧝 Scheda Eroe")
    if st.session_state.game_phase != "creazione":
        st.subheader(f"{st.session_state.personaggio['nome']} (Lv. {st.session_state.livello})")
        
        # Gestione Vita e Morte
        if st.session_state.hp <= 0:
            st.error("💀 SEI MORTO")
            if st.button("Resuscita (Costo: 50 Oro)"):
                if st.session_state.oro >= 50:
                    st.session_state.oro -= 50
                    st.session_state.hp = st.session_state.hp_max // 2
                    st.rerun()
        else:
            st.metric("Punti Vita", f"{st.session_state.hp} / {st.session_state.hp_max}")
            st.progress(max(0.0, min(1.0, st.session_state.hp / st.session_state.hp_max)))
        
        # Progresso XP
        prossimo = st.session_state.livello * 100
        st.write(f"XP: {st.session_state.xp} / {prossimo}")
        st.progress(st.session_state.xp / prossimo)
        
        st.metric("💰 Oro", f"{st.session_state.oro} gp")
        
        st.subheader("🎒 Zaino")
        st.write(", ".join(st.session_state.inventario))
        
        st.divider()
        if st.button("🎲 Tira d20", use_container_width=True, disabled=st.session_state.hp <= 0):
            st.session_state.ultimo_tiro = random.randint(1, 20)
            st.toast(f"Hai ottenuto un {st.session_state.ultimo_tiro}!")

    st.subheader("💾 Salvataggio")
    st.download_button("Esporta Storia", 
                       "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages]), 
                       file_name="campagna_dnd.txt")

# --- LOGICA DI GIOCO ---
st.title("🧙‍♂️ D&D Engine Professional 2026")

if st.session_state.game_phase == "creazione":
    st.subheader("Creazione dell'Eroe")
    with st.form("char_form"):
        nome = st.text_input("Nome")
        razza = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Tiefling"])
        classe = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Chierico"])
        if st.form_submit_button("Inizia l'Avventura") and nome:
            st.session_state.personaggio = {"nome": nome, "razza": razza, "classe": classe}
            st.session_state.game_phase = "playing"
            st.rerun()

elif st.session_state.hp <= 0:
    st.warning("La tua avventura si è interrotta. Resuscita dalla scheda eroe o ricarica la pagina.")

else:
    if not st.session_state.messages:
        p = st.session_state.personaggio
        intro = model.generate_content(f"DM mode. Inizia avventura per {p['nome']}, {p['razza']} {p['classe']}. [[IMMAGINE:scena iniziale]]")
        st.session_state.messages.append({"role": "assistant", "content": intro.text})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        sys_prompt = f"""
        GIOCATORE: {st.session_state.personaggio} | HP: {st.session_state.hp}/{st.session_state.hp_max}
        ORO: {st.session_state.oro} | TIRO DADO: {st.session_state.ultimo_tiro}
        
        REGOLE:
        1. Se il TIRO DADO è presente, usalo per determinare il successo. Se non c'è e l'azione è difficile, chiedi al giocatore di tirare il dado.
        2. Usa i tag: [[DANNO:X]], [[CURA:X]], [[ORO:X]], [[XP:X]], [[PRENDI:Oggetto]], [[IMMAGINE:descrizione]].
        3. Se HP <= 0, descrivi la caduta dell'eroe.
        """
        
        with st.chat_message("assistant"):
            response = model.generate_content(sys_prompt + "\n" + prompt)
            out = response.text
            
            # Parsing integrato
            if "[[IMMAGINE:" in out: genera_immagine(out.split("[[IMMAGINE:")[1].split("]]")[0])
            if "[[DANNO:" in out: st.session_state.hp -= int(out.split("[[DANNO:")[1].split("]]")[0])
            if "[[XP:" in out: st.session_state.xp += int(out.split("[[XP:")[1].split("]]")[0])
            if "[[ORO:" in out: st.session_state.oro += int(out.split("[[ORO:")[1].split("]]")[0])
            if "[[PRENDI:" in out: st.session_state.inventario.append(out.split("[[PRENDI:")[1].split("]]")[0])

            controlla_livello()
            st.markdown(out)
            st.session_state.messages.append({"role": "assistant", "content": out})
            st.session_state.ultimo_tiro = None # Reset dado dopo l'uso
            st.rerun()
