import streamlit as st
import sqlite3
import base64
from io import BytesIO
from pypdf import PdfReader
from PIL import Image
from groq import Groq

st.set_page_config(page_title="Venu AI Ultimate", page_icon="🚀", layout="wide")

# API Key
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# உங்கள் Groq கணக்கில் வேலை செய்யும் மாடல்களை எடுத்தல்
@st.cache_data(ttl=3600)
def get_all_models():
    try:
        models = client.models.list()
        all_ids = [
            m.id for m in models.data 
            if not any(x in m.id.lower() for x in ["whisper", "guard", "tts", "playai"])
        ]
        return all_ids if all_ids else ["llama-3.3-70b-versatile"]
    except Exception:
        return ["llama-3.3-70b-versatile"]

available_models = get_all_models()

# போட்டோவைப் பார்க்கக்கூடிய Vision மாடலைத் தனியாகக் கண்டுபிடித்தல்
vision_candidates = [
    m for m in available_models 
    if any(k in m.lower() for k in ["scout", "maverick", "vision"])
]
default_vision_model = vision_candidates[0] if vision_candidates else "meta-llama/llama-4-scout-17b-16e-instruct"

# Database (History சேமிக்க)
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
    st.title("⚙️ Venu AI Settings")
    username = st.text_input("உங்கள் பெயர்:", value="Venugopal").strip().lower()
    selected_model = st.selectbox("Text AI Model:", available_models)
    ai_mode = st.selectbox(
        "AI Mode:",
        ["General Assistant", "Study & Exam Tutor", "Coding & Tech Expert"]
    )
    st.caption(f"📷 Vision Model: `{default_vision_model}`")
    
    if st.button("🗑️ என் History-ஐ அழி"):
        c.execute("DELETE FROM chat_logs WHERE username = ?", (username,))
        conn.commit()
        st.rerun()

mode_prompts = {
    "General Assistant": "நீங்கள் ஒரு புத்திசாலித்தனமான AI உதவியாளர். தெளிவாகப் பதில் அளியுங்கள்.",
    "Study & Exam Tutor": "நீங்கள் ஒரு சிறந்த ஆசிரியர். மாணவர்களுக்குப் புரியும்படி எளிய உதாரணங்களுடன் பாடம் நடத்துங்கள்.",
    "Coding & Tech Expert": "நீங்கள் ஒரு சீனியர் சாஃப்ட்வேர் டெவலப்பர். சுத்தமான கோட் மற்றும் விளக்கங்களைத் தாருங்கள்."
}

# --- Main Screen ---
st.title("🚀 Venu AI Ultimate")
st.caption(f"User: **{username.capitalize()}** | Mode: **{ai_mode}**")

c.execute("SELECT role, content FROM chat_logs WHERE username = ?", (username,))
user_history = c.fetchall()

for role, content in user_history:
    with st.chat_message(role):
        st.markdown(content)

# --- கீழே Chat Box-லேயே File Upload வசதி ---
prompt_data = st.chat_input(
    "கேள்வியைக் கேளுங்கள் (அல்லது + அழுத்தி ஃபைல் சேர்க்கவும்)...",
    accept_file=True,
    file_type=["pdf", "txt", "jpg", "jpeg", "png"]
)

if prompt_data:
    user_query = prompt_data.text or "இந்த ஃபைலைப் பற்றி விளக்கவும்."
    uploaded_files = prompt_data.files

    file_text = ""
    base64_image = None

    with st.chat_message("user"):
        if uploaded_files:
            uploaded_file = uploaded_files[0]
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    file_text += page.extract_text() or ""
                st.info(f"📄 PDF படிக்கப்பட்டது: {uploaded_file.name}")
            elif uploaded_file.type == "text/plain":
                file_text = uploaded_file.read().decode("utf-8")
                st.info(f"📝 Text படிக்கப்பட்டது: {uploaded_file.name}")
            elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                img = Image.open(uploaded_file)
                st.image(img, width=250)
                # போட்டோ அளவைக் குறைத்து Base64 ஆக மாற்றுதல்
                img.thumbnail((1024, 1024))
                buffered = BytesIO()
                img.convert("RGB").save(buffered, format="JPEG", quality=85)
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        st.markdown(user_query)

    c.execute("INSERT INTO chat_logs (username, role, content) VALUES (?, ?, ?)", (username, "user", user_query))
    conn.commit()

    recent_chat = "\n".join([f"{r}: {m}" for r, m in user_history[-6:]])
    system_content = f"""
    {mode_prompts[ai_mode]}
    முந்தைய உரையாடல்: {recent_chat}
    ஆவணத்தின் விவரம்: {file_text[:18000] if file_text else "ஆவணம் இல்லை."}
    """

    with st.chat_message("assistant"):
        with st.spinner("சிந்திக்கிறது..."):
            try:
                if base64_image:
                    # போட்டோ இருந்தால் Vision மாடலுக்கு அனுப்புதல்
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"{mode_prompts[ai_mode]}\n\nகேள்வி: {user_query}"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                                ],
                            }
                        ],
                        model=default_vision_model,
                    )
                else:
                    # சாதாரண மெசேஜ் அல்லது PDF என்றால் String ஆக அனுப்புதல்
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": str(system_content)},
                            {"role": "user", "content": str(user_query)}
                        ],
                        model=selected_model,
                    )
                
                ai_reply = chat_completion.choices[0].message.content
                st.markdown(ai_reply)

                c.execute("INSERT INTO chat_logs (username, role, content) VALUES (?, ?, ?)", (username, "assistant", ai_reply))
                conn.commit()
            except Exception as e:
                st.error(f"பிழை: {e}")
