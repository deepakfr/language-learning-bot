import streamlit as st
import sqlite3
import requests
import os
from datetime import datetime
from fpdf import FPDF
from io import BytesIO
from gtts import gTTS
import tempfile

# --- DB Path Fix for Streamlit Cloud ---
DB_PATH = os.path.join(os.path.expanduser("~"), "mistakes.db")

# --- Load API Key ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- Page Config ---
st.set_page_config(page_title="🌐 Language Learning Chatbot", layout="centered")
st.title("🌐 Deep Language Learning Chatbot")
st.markdown("Practice any language with an AI chatbot. Get real-time feedback and track your mistakes. Blended by Deepak Labs")

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
    known_lang = st.text_input("Your known language", "English")
    target_lang = st.text_input("Language you want to learn", "Spanish")
    level = st.selectbox("Your level", ["Beginner", "Intermediate", "Advanced"])

    if st.button("Reset Chat"):
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
                st.markdown(f"⚠️ Correction:** {message}")
    else:
        st.info("No conversation yet.")

# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Chat Input (Text Only) ---
st.subheader("✍️ Type in your target language:")
user_input = st.text_area("Your message:", "", height=100)
send_btn = st.button("Send")

if send_btn and user_input.strip() != "":
    # --- Prompt Construction ---
    context = f"""You are a friendly and supportive language tutor.
You are chatting in {target_lang} with a user who speaks {known_lang} and is at a {level} level.
Keep the conversation flowing, correct mistakes gently if needed, and encourage the user.

User says: {user_input}
Respond in {target_lang}:"""

    bot_response = groq_chat(context)

    # --- Log Chat ---
    st.session_state.chat_history.append(("You", user_input))
    st.session_state.chat_history.append(("Bot", bot_response))

    # --- Voice Output (Bot's response) ---
    try:
        tts = gTTS(bot_response, lang=target_lang[:2].lower())
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name, format="audio/mp3")
    except Exception as e:
        st.error(f"Voice output error: {e}")

    # --- Correction ---
    correction_prompt = f"""Here is a sentence by a {target_lang} learner:
"{user_input}"

If there are any mistakes, correct them and specify the type (grammar, vocab, syntax).
If correct, say "No mistakes found.".
Respond in {known_lang}."""

    correction_result = groq_chat(correction_prompt)

    if "No mistakes" not in correction_result:
        log_mistake(user_input, correction_result, "language mistake")
        st.session_state.chat_history.append(("Correction", correction_result))

# --- Display last messages ---
if st.session_state.chat_history:
    st.markdown("---")
    st.subheader("💬 Latest Messages")
    last_messages = st.session_state.chat_history[-3:]
    for role, text in last_messages:
        if role == "You":
            st.markdown(f"**🧑 You:** {text}")
        elif role == "Bot":
            st.markdown(f"**🤖 Bot:** {text}")
        elif role == "Correction":
            st.markdown(f"⚠️ **Correction:** {text}")

# --- Summary Button ---
st.markdown("---")
if st.button("📊 Show Mistake Summary"):
    summary = get_mistakes_summary()
    if summary:
        st.subheader("Common Mistakes:")
        for error_type, count in summary:
            st.markdown(f"- **{error_type}**: {count} time(s)")
    else:
        st.info("No mistakes logged yet.")
