import streamlit as st
from streamlit_webrtc import webrtc_streamer
from fpdf import FPDF
from io import BytesIO
import sqlite3
import requests

# Setup
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# Session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Chat API
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
    return response.json()["choices"][0]["message"]["content"]

# PDF Generator
def generate_pdf(chat_history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for role, text in chat_history:
        label = {"You": "🧑 You", "Bot": "🤖 Bot", "Correction": "⚠️ Correction"}.get(role, role)
        pdf.multi_cell(0, 10, f"{label}: {text}")
        pdf.ln()
    pdf_file = BytesIO()
    pdf.output(pdf_file)
    pdf_file.seek(0)
    return pdf_file

# UI
st.title("🌐 Language Chatbot + Voice")
user_input = st.text_area("✍️ Type your message:")

# Voice input display (placeholder)
st.info("🎤 Voice input capture (placeholder):")
webrtc_streamer(key="mic", audio_receiver_size=1024)

if st.button("Send"):
    prompt = f"You are a language tutor. Respond to this message in the target language:\n{user_input}"
    bot_response = groq_chat(prompt)

    st.session_state.chat_history.append(("You", user_input))
    st.session_state.chat_history.append(("Bot", bot_response))

# Display latest
if st.session_state.chat_history:
    last = st.session_state.chat_history[-2:]
    for role, text in last:
        st.markdown(f"**{role}:** {text}")

# PDF Export
if st.button("📄 Export as PDF"):
    pdf = generate_pdf(st.session_state.chat_history)
    st.download_button("⬇️ Download PDF", data=pdf, file_name="chat.pdf", mime="application/pdf")
