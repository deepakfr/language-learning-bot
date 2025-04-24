import streamlit as st
import sqlite3
import requests
import os
from datetime import datetime
from fpdf import FPDF
from io import BytesIO
from gtts import gTTS
import tempfile
from streamlit_js_eval import streamlit_js_eval

# --- DB Path Fix for Streamlit Cloud ---
DB_PATH = os.path.join(os.path.expanduser("~"), "mistakes.db")

# --- Load API Key ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- Page Config ---
st.set_page_config(page_title="🌐 Voice Translator Chatbot", layout="centered")
st.title("🌐 Voice Translator & Language Tutor")
st.markdown("Speak in your language, get translated voice replies. Practice and improve your skills.")

# --- DB Setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            corrected_output TEXT,
            error_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Logging Mistakes ---
def log_mistake(user_input, corrected_output, error_type):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO mistakes (user_input, corrected_output, error_type) VALUES (?, ?, ?)",
                  (user_input, corrected_output, error_type))
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        st.error(f"Database error: {e}")

# --- Mistake Summary ---
def get_mistakes_summary():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT error_type, COUNT(*) FROM mistakes GROUP BY error_type")
    results = c.fetchall()
    conn.close()
    return results

# --- Groq Chat Completion ---
def groq_chat(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    response = requests.post(url, headers=headers, json=payload)

    try:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

# --- Sidebar ---
with st.sidebar:
    st.header("🌍 Language Setup")
    known_lang = st.text_input("🎤 You speak", "English")
    target_lang = st.text_input("🎯 You want to speak", "Spanish")
    level = st.selectbox("📚 Your level", ["Beginner", "Intermediate", "Advanced"])

    if st.button("🔁 Reset Chat"):
        st.session_state.chat_history = []
        st.success("Conversation reset.")

    st.markdown("---")
    st.subheader("🕘 Chat History")
    if "chat_history" in st.session_state and st.session_state.chat_history:
        for role, message in st.session_state.chat_history:
            if role == "You":
                st.markdown(f"**🧑 You:** {message}")
            elif role == "Bot":
                st.markdown(f"**🤖 Bot:** {message}")
            elif role == "Correction":
                st.markdown(f"**⚠️ Correction:** {message}")
    else:
        st.info("No conversation yet.")

    if st.session_state.get("chat_history"):
        st.markdown("---")
        st.subheader("📄 Export")
        if st.button("📥 Download PDF"):
            buffer = BytesIO()
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Language Learning Chat", ln=True, align="C")
            pdf.ln(10)
            for role, msg in st.session_state.chat_history:
                label = "🧑 You" if role == "You" else "🤖 Bot" if role == "Bot" else "⚠️ Correction"
                pdf.multi_cell(0, 10, f"{label}: {msg}")
                pdf.ln(2)
            pdf.output(buffer)
            buffer.seek(0)
            st.download_button("📄 Download Chat History", buffer, file_name="chat_history.pdf")

# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Voice Input ---
st.subheader("🎙️ Speak in your language or type below:")
voice_input = streamlit_js_eval(js_expressions="window.prompt('🎤 Speak your sentence aloud then click OK')", key="voice")
text_input = st.text_area("Or type your message here:", "", height=100)

user_input = voice_input if voice_input else text_input

# --- Send Button ---
if st.button("Translate & Speak") and user_input.strip():
    # --- Translate Prompt ---
    prompt = f"""You are a translation assistant.
Translate this message from {known_lang} into {target_lang}, and make it sound natural.

Input: {user_input}
Output:"""

    bot_response = groq_chat(prompt)
    st.session_state.chat_history.append(("You", user_input))
    st.session_state.chat_history.append(("Bot", bot_response))

    try:
        tts = gTTS(bot_response, lang=target_lang[:2].lower())
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name, format="audio/mp3")
    except Exception as e:
        st.error(f"Voice output error: {e}")

    # --- Correction Check ---
    correction_prompt = f"""Here is a sentence by a {target_lang} learner:
"{user_input}"

If there are any mistakes, correct them and specify the type (grammar, vocab, syntax).
If correct, say \"No mistakes found.\".
Respond in {known_lang}."""

    correction_result = groq_chat(correction_prompt)

    if "No mistakes" not in correction_result:
        log_mistake(user_input, correction_result, "language mistake")
        st.session_state.chat_history.append(("Correction", correction_result))

# --- Display Last Messages ---
if st.session_state.chat_history:
    st.markdown("---")
    st.subheader("🧾 Latest Messages")
    for role, text in st.session_state.chat_history[-3:]:
        if role == "You":
            st.markdown(f"**🧑 You:** {text}")
        elif role == "Bot":
            st.markdown(f"**🤖 Bot:** {text}")
        elif role == "Correction":
            st.markdown(f"**⚠️ Correction:** {text}")

# --- Summary ---
st.markdown("---")
if st.button("📊 Show Mistake Summary"):
    summary = get_mistakes_summary()
    if summary:
        st.subheader("Common Mistakes:")
        for error_type, count in summary:
            st.markdown(f"- **{error_type}**: {count} time(s)")
    else:
        st.info("No mistakes logged yet.")
