import streamlit as st
import sqlite3
import base64
from io import BytesIO
from pypdf import PdfReader
from PIL import Image
from groq import Groq

st.set_page_config(page_title="Venu AI Ultimate", page_icon="🚀", layout="wide")

# உங்கள் Secrets-ல் உள்ள GROQ_API_KEY-ஐப் பயன்படுத்துதல்
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Database (தனித்தனி User History)
conn = sqlite3.connect("advanced_chat.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        role TEXT,
        content TEXT
    )
""")
conn.commit()

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Venu AI Control")
    username = st.text_input("உங்கள் பெயர்:", value="Venugopal").strip().lower()
    
    ai_mode = st.selectbox(
        "AI Mode:",
        ["General Assistant", "Study & Exam Tutor", "Coding & Tech Expert"]
    )
    
    st.divider()
    st.subheader("📁 File / Photo Upload")
    uploaded_file = st.file_uploader(
        "PDF, TXT அல்லது போட்டோ (JPG/PNG):",
        type=["pdf", "txt", "jpg", "jpeg", "png"]
    )
    
    if st.button("🗑️ என் History-ஐ அழி"):
        c.execute("DELETE FROM chat_logs WHERE username = ?", (username,))
        conn.commit()
        st.rerun()

mode_prompts = {
    "General Assistant": "நீங்கள் ஒரு புத்திசாலித்தனமான AI உதவியாளர். தெளிவாகப் பதில் அளியுங்கள்.",
    "Study & Exam Tutor": "நீங்கள் ஒரு சிறந்த ஆசிரியர். மாணவர்களுக்குப் புரியும்படி எளிய உதாரணங்கள் மற்றும் முக்கியப் புள்ளிகளுடன் பாடம் நடத்துங்கள்.",
    "Coding & Tech Expert": "நீங்கள் ஒரு சீனியர் சாஃப்ட்வேர் டெவலப்பர். சுத்தமான கோட் மற்றும் விளக்கங்களைத் தாருங்கள்."
}

# ஃபைல் & போட்டோ படிக்கும் பகுதி
file_text = ""
base64_image = None

if uploaded_file is not None:
    file_type = uploaded_file.type
    if file_type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            file_text += page.extract_text() or ""
        st.sidebar.success(f"PDF படிக்கப்பட்டது ({len(reader.pages)} பக்கங்கள்)")
    elif file_type == "text/plain":
        file_text = uploaded_file.read().decode("utf-8")
        st.sidebar.success("Text ஃபைல் தயார்!")
    elif file_type in ["image/jpeg", "image/png", "image/jpg"]:
        img = Image.open(uploaded_file)
        st.sidebar.image(img, caption="அப்லோட் செய்த படம்", use_container_width=True)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

# --- Main Screen ---
st.title(f"🚀 Venu AI Ultimate ({ai_mode})")
st.caption(f"Logged in as: **{username.capitalize()}**")

c.execute("SELECT role, content FROM chat_logs WHERE username = ?", (username,))
user_history = c.fetchall()

for role, content in user_history:
    with st.chat_message(role):
        st.markdown(content)

user_query = st.chat_input("கேள்வியைக் கேளுங்கள் அல்லது ஃபைல் பற்றி விசாரியுங்கள்...")

if user_query:
    with st.chat_message("user"):
        st.markdown(user_query)
    c.execute("INSERT INTO chat_logs (username, role, content) VALUES (?, ?, ?)", (username, "user", user_query))
    conn.commit()

    recent_chat = "\n".join([f"{r}: {m}" for r, m in user_history[-6:]])

    system_content = f"""
    {mode_prompts[ai_mode]}
    
    முந்தைய உரையாடல்:
    {recent_chat}
    
    அப்லோட் செய்யப்பட்ட ஆவணம்:
    {file_text[:18000] if file_text else "ஆவணம் இல்லை."}
    """

    with st.chat_message("assistant"):
        with st.spinner("சிந்திக்கிறது..."):
            if base64_image:
                # போட்டோ அப்லோட் செய்தால் Groq Vision மாடல் பயன்படுத்தும்
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"{system_content}\n\nகேள்வி: {user_query}"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                            ],
                        }
                    ],
                    model="llama-3.2-90b-vision-preview",
                )
            else:
                # சாதாரண கேள்வி மற்றும் PDF-க்கு Llama-3.3-70b மாடல் பயன்படுத்தும்
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": user_query}
                    ],
                    model="llama-3.3-70b-versatile",
                )
            
            ai_reply = chat_completion.choices[0].message.content
            st.markdown(ai_reply)

    c.execute("INSERT INTO chat_logs (username, role, content) VALUES (?, ?, ?)", (username, "assistant", ai_reply))
    conn.commit()
    
