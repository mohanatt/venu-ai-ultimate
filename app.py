import streamlit as st
import sqlite3
from pypdf import PdfReader
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="My Advanced AI", page_icon="🚀", layout="wide")

# API Key செட்டப்
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Database (ஒவ்வொரு பயனருக்கும் தனி History சேமிக்க)
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

# --- Sidebar: User Profile, Mode & File Upload ---
with st.sidebar:
    st.title("⚙️ AI Control Panel")
    
    # 1. நண்பர்களுக்கான தனித்தனி பெயர் (Private History-க்காக)
    username = st.text_input("உங்கள் பெயர் (History சேமிக்க):", value="Venugopal").strip().lower()
    
    # 2. AI Mode தேர்வு
    ai_mode = st.selectbox(
        "AI Mode தேர்ந்தெடுக்கவும்:",
        ["General Assistant", "Study & Exam Tutor", "Coding & Tech Expert"]
    )
    
    st.divider()
    
    # 3. File Upload (PDF, TXT, மற்றும் Images)
    st.subheader("📁 File / Photo Upload")
    uploaded_file = st.file_uploader(
        "PDF, TXT அல்லது போட்டோ (JPG/PNG) அப்லோட் செய்யவும்:",
        type=["pdf", "txt", "jpg", "jpeg", "png"]
    )
    
    if st.button("🗑️ என் History-ஐ அழி"):
        c.execute("DELETE FROM chat_logs WHERE username = ?", (username,))
        conn.commit()
        st.rerun()

# System Instruction அமைத்தல்
mode_prompts = {
    "General Assistant": "நீங்கள் ஒரு புத்திசாலித்தனமான, நட்பான AI உதவியாளர். தெளிவாகவும் சுருக்கமாகவும் பதில் அளியுங்கள்.",
    "Study & Exam Tutor": "நீங்கள் ஒரு சிறந்த ஆசிரியர். மாணவர்களுக்குப் புரியும்படி எளிய உதாரணங்கள் மற்றும் முக்கியப் புள்ளிகளுடன் (Bullet points) பாடம் நடத்துங்கள்.",
    "Coding & Tech Expert": "நீங்கள் ஒரு சீனியர் சாஃப்ட்வேர் ஆர்க்கிடெக்ட். சுத்தமான கோட் மற்றும் பிழைகளைச் சரிசெய்யும் வழிகளைத் தெளிவாகக் கூறுங்கள்."
}

# அப்லோட் செய்த ஃபைலைத் தயார் செய்தல்
file_text = ""
uploaded_image = None

if uploaded_file is not None:
    file_type = uploaded_file.type
    if file_type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            file_text += page.extract_text() or ""
        st.sidebar.success(f"PDF படிக்கப்பட்டது ({len(reader.pages)} பக்கங்கள்)")
    elif file_type == "text/plain":
        file_text = uploaded_file.read().decode("utf-8")
        st.sidebar.success("Text ஃபைல் தயாராக உள்ளது!")
    elif file_type in ["image/jpeg", "image/png", "image/jpg"]:
        uploaded_image = Image.open(uploaded_file)
        st.sidebar.image(uploaded_image, caption="அப்லோட் செய்த படம்", use_container_width=True)

# --- Main Chat Screen ---
st.title(f"🚀 Smart AI ({ai_mode})")
st.caption(f"Logged in as: **{username.capitalize()}** | உங்கள் உரையாடல்கள் பாதுகாப்பாகச் சேமிக்கப்படும்.")

# குறிப்பிட்ட நபரின் பழைய History-ஐ மட்டும் எடுத்தல்
c.execute("SELECT role, content FROM chat_logs WHERE username = ?", (username,))
user_history = c.fetchall()

for role, content in user_history:
    with st.chat_message(role):
        st.markdown(content)

# புதிய கேள்வி
user_query = st.chat_input("கேள்வியைக் கேளுங்கள் அல்லது ஃபைல் பற்றி விசாரியுங்கள்...")

if user_query:
    # பயனர் கேள்வியைக் காட்டி சேமித்தல்
    with st.chat_message("user"):
        st.markdown(user_query)
    c.execute("INSERT INTO chat_logs (username, role, content) VALUES (?, ?, ?)", (username, "user", user_query))
    conn.commit()

    # கடைசி 6 மெசேஜ்களை Memory-க்காக எடுத்தல்
    recent_chat = "\n".join([f"{r}: {m}" for r, m in user_history[-6:]])

    full_prompt = f"""
    {mode_prompts[ai_mode]}

    முந்தைய உரையாடல் சுருக்கம் (Memory):
    {recent_chat}

    அப்லோட் செய்யப்பட்ட ஆவணத்தின் விவரம்:
    {file_text[:20000] if file_text else "ஆவணம் எதுவும் அப்லோட் செய்யப்படவில்லை."}

    பயனரின் தற்போதைய கேள்வி: {user_query}
    """

    # AI-க்கு அனுப்ப வேண்டிய உள்ளடக்கம் (Text + Image இருந்தால் Image)
    contents_to_send = [full_prompt]
    if uploaded_image is not None:
        contents_to_send.append(uploaded_image)

    with st.chat_message("assistant"):
        with st.spinner("சிந்திக்கிறது..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents_to_send
            )
            ai_reply = response.text
            st.markdown(ai_reply)

    # AI பதிலை DB-ல் சேமித்தல்
    c.execute("INSERT INTO chat_logs (username, role, content) VALUES (?, ?, ?)", (username, "assistant", ai_reply))
    conn.commit()
        
