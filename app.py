import streamlit as st
import openai
import re
from db import save_verdict, get_recent_verdicts

# ✅ Groq API credentials
openai.api_key = st.secrets["GROQ_API_KEY"]
openai.api_base = "https://api.groq.com/openai/v1"

# 🧠 Analyze conflict using Groq
def analyze_conflict(user1_input, user2_input, theme, user1_name, user2_name):
    system_prompt = (
        f"You are JudgeBot, an unbiased AI judge for {theme.lower()} conflicts. "
        "Analyze both sides, highlight key points, and give a fair verdict. "
        "Clearly state who is more reasonable and provide a win percentage (e.g., 60% vs 40%)."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"{user1_name} says:\n{user1_input}\n\n"
                       f"{user2_name} says:\n{user2_input}\n\n"
                       f"Who is more reasonable and why? Show the win percentage too.",
        },
    ]

    try:
        response = openai.ChatCompletion.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {e}"

# 📊 Extract win percentages from JudgeBot's response
def extract_percentages(verdict_text):
    match = re.findall(r"(\b\d{1,3})%", verdict_text)
    if len(match) >= 2:
        p1, p2 = int(match[0]), int(match[1])
        return p1, p2
    return None, None

# 📤 Generate WhatsApp Link
def generate_whatsapp_link(phone_number, message):
    phone_number = phone_number.replace("+", "").replace("-", "").replace(" ", "")
    message = message.replace(" ", "%20").replace("\n", "%0A")
    return f"https://wa.me/{phone_number}?text={message}"

# 📤 Generate Email Link
def generate_mailto_link(email, subject, body):
    subject = subject.replace(" ", "%20")
    body = body.replace(" ", "%20").replace("\n", "%0A")
    return f"mailto:{email}?subject={subject}&body={body}"

# 💬 Conflict Interface
def show_interface(theme):
    st.subheader(f"{theme} Conflict Arbitration ⚖️")
    st.write("Describe the conflict from both perspectives. JudgeBot will decide fairly.")

    with st.form(key="conflict_form"):
        user1_name = st.text_input("🧑 User 1: Name", key="user1_name")
        user2_name = st.text_input("👩 User 2: Name", key="user2_name")
        contact_email = st.text_input("📧 Email of User 2 (optional)")
        contact_phone = st.text_input("📱 WhatsApp Number of User 2 (optional, with country code)")
        user1_input = st.text_area("🧑 User 1: Your version", key="user1_input")
        user2_input = st.text_area("👩 User 2: Your version", key="user2_input")
        submit = st.form_submit_button("🧠 Get Verdict from JudgeBot")

    if submit:
        if not all([user1_name, user2_name, user1_input, user2_input]):
            st.warning("Please enter both names and both sides of the conflict.")
            return

        with st.spinner("JudgeBot is thinking..."):
            verdict = analyze_conflict(user1_input, user2_input, theme, user1_name, user2_name)
            save_verdict(theme, user1_name, user2_name, user1_input, user2_input, verdict)

        # 🎯 Show current verdict only
        st.success("✅ Verdict delivered!")
        st.markdown("### 🧑‍⚖️ JudgeBot says:")
        st.markdown(verdict)

        # Percentages
        p1, p2 = extract_percentages(verdict)
        if p1 is not None and p2 is not None:
            st.markdown("### 🏆 Victory Margin")
            st.progress(p1 / 100.0, f"{user1_name}: {p1}%")
            st.progress(p2 / 100.0, f"{user2_name}: {p2}%")
        else:
            st.info("Could not extract win percentages. Try rephrasing the prompt.")

        # Share
        if contact_email or contact_phone:
            st.markdown("### 📤 Share the Verdict")
            prefilled_message = f"""Hello {user2_name},

JudgeBot has delivered a verdict on your conflict with {user1_name}.

📜 Verdict:
{verdict}

Visit the app to respond or review more: http://localhost:8501

🤖 Sent via FairFight AI
"""
            if contact_phone:
                wa_link = generate_whatsapp_link(contact_phone, prefilled_message)
                st.markdown(f"[📲 Send via WhatsApp]({wa_link})", unsafe_allow_html=True)

            if contact_email:
                mail_link = generate_mailto_link(contact_email, f"JudgeBot Verdict for {theme}", prefilled_message)
                st.markdown(f"[📧 Send via Email]({mail_link})", unsafe_allow_html=True)

# 🏠 App main
def main():
    st.set_page_config(page_title="FairFight AI", page_icon="⚖️")
    st.title("🤖 FairFight AI")
    st.caption("Because every conflict deserves a fair verdict.")

    # Tabs layout: Main & History
    tab = st.sidebar.radio("🗂 Menu", ["🧠 New Verdict", "📜 Verdict History"])

    if tab == "🧠 New Verdict":
        theme = st.selectbox("Choose a conflict type:", ["Couple 💔", "Friends 🎭", "Pro 👨‍💼"])
        show_interface(theme.split()[0])

    elif tab == "📜 Verdict History":
        st.sidebar.write("🔄 Refresh to update list.")
        verdicts = get_recent_verdicts()
        st.subheader("🧾 Past Verdicts")
        if verdicts:
            for row in verdicts:
                with st.expander(f"⚖️ {row['theme']} - {row['user1_name']} vs {row['user2_name']} ({row['created_at']})"):
                    st.markdown(f"**🧑 {row['user1_name']} says:**\n{row['user1_input']}")
                    st.markdown(f"**👩 {row['user2_name']} says:**\n{row['user2_input']}")
                    st.markdown(f"**Verdict:**\n{row['verdict']}")
        else:
            st.info("No verdicts found yet.")

if __name__ == "__main__":
    main()
