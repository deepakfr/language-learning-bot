import streamlit as st
import sqlite3
import requests
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# Load API key from secrets
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# -- Page Config
st.set_page_config(page_title="🌐 Language Learning Chatbot", layout="centered")
st.title("🌐 Deep Language Learning Chatbot")
st.markdown("Practice any language with an AI chatbot. Get real-time feedback and track your mistakes. Blended by deepak labs")

# --- DB Setup ---
def init_db():
    conn = sqlite3.connect("mistakes.db")
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

def log_mistake(user_input, corrected_output, error_type):
    conn = sqlite3.connect("mistakes.db")
    c = conn.cursor()
    c.execute("INSERT INTO mistakes (user_input, corrected_output, error_type) VALUES (?, ?, ?)",
              (user_input, corrected_output, error_type))
    conn.commit()
    conn.close()

def get_mistakes_summary():
    conn = sqlite3.connect("mistakes.db")
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


# --- Sidebar for Settings ---
with st.sidebar:
    st.header("Language Setup")
    known_lang = st.text_input("Your known language", "English")
    target_lang = st.text_input("Language you want to learn", "Spanish")
    level = st.selectbox("Your level", ["Beginner", "Intermediate", "Advanced"])

    if st.button("Reset Chat"):
        st.session_state.chat_history = []
        st.success("Conversation reset.")

# --- Session state for memory ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Chat Interface ---
st.subheader("Start chatting in your target language:")

user_input = st.text_area("✍️ Enter your message:", "", height=100)
send_btn = st.button("Send")

if send_btn and user_input.strip() != "":
    # Chatbot prompt (contextualized)
    context = f"""You are a friendly and supportive language tutor.
You are chatting in {target_lang} with a user who speaks {known_lang} and is at a {level} level.
Keep the conversation flowing, correct mistakes gently if needed, and encourage the user.

User says: {user_input}
Respond in {target_lang}:"""

    bot_response = groq_chat(context)

    # Log chat
    st.session_state.chat_history.append(("You", user_input))
    st.session_state.chat_history.append(("Bot", bot_response))

    # --- Error detection ---
    correction_prompt = f"""Here is a sentence by a {target_lang} learner:
"{user_input}"

If there are any mistakes, correct them and specify the type (grammar, vocab, syntax).
If correct, say "No mistakes found.".
Respond in {known_lang}."""

    correction_result = groq_chat(correction_prompt)

    if "No mistakes" not in correction_result:
        log_mistake(user_input, correction_result, "language mistake")
        st.session_state.chat_history.append(("Correction", correction_result))

# --- Display most recent interaction only ---
if st.session_state.chat_history:
    last_messages = st.session_state.chat_history[-3:]  # You, Bot, Correction (if exists)
    for role, text in last_messages:
        if role == "You":
            st.markdown(f"**🧑 You:** {text}")
        elif role == "Bot":
            st.markdown(f"**🤖 Bot:** {text}")
        elif role == "Correction":
            st.markdown(f"⚠️ **Correction:** {text}")

# --- Mistake Summary ---
st.markdown("---")
if st.button("📊 Show Mistake Summary"):
    summary = get_mistakes_summary()
    if summary:
        st.subheader("Common Mistakes:")
        for error_type, count in summary:
            st.markdown(f"- **{error_type}**: {count} time(s)")
    else:
        st.info("No mistakes logged yet.")


