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

# உங்கள் Groq கணக்கில் வேலை செய்யும் மாடல்களைத் தானாகக் கண்டுபிடித்தல்
@st.cache_data(ttl=3600)
def get_working_models():
    try:
        models = client.models.list()
        chat_models = [
            m.id for m in models.data 
            if not any(x in m.id.lower() for x in ["whisper", "guard", "tts", "playai"])
        ]
        return chat_models if chat_models else ["gemma2-9b-it"]
    except Exception:
        return ["gemma2-9b-it"]

available_models = get_working_models()

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

# --- Sidebar (செட்டிங்ஸ் மட்டும்) ---
with st.sidebar:
    st.title("⚙️ Venu AI Settings")
    username = st.text_input("உங்கள் பெயர்:", value="Venugopal").strip().lower()
    selected_model = st.selectbox("AI Model:", available_models)
    ai_mode = st.selectbox(
        "AI Mode:",
        ["General Assistant", "Study & Exam Tutor", "Coding & Tech Expert"]
    )
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
st.title(f"🚀 Venu AI Ultimate")
st.caption(f"User: **{username.capitalize()}** | Mode: **{ai_mode}** | Model: `{selected_model}`")

# பழைய History-ஐ காட்டுதல்
c.execute("SELECT role, content FROM chat_logs WHERE username = ?", (username,))
user_history = c.fetchall()

for role, content in user_history:
    with st.chat_message(role):
        st.markdown(content)

# --- கீழே Chat Box-லேயே File Upload வசதி! ---
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
                st.info(f"📄 அப்லோட் ஆனது: {uploaded_file.name}")
            elif uploaded_file.type == "text/plain":
                file_text = uploaded_file.read().decode("utf-8")
                st.info(f"📝 அப்லோட் ஆனது: {uploaded_file.name}")
            elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                img = Image.open(uploaded_file)
                st.image(img, width=250)
                buffered = BytesIO()
                img.convert("RGB").save(buffered, format="JPEG")
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
                    vision_models = [m for m in available_models if any(v in m.lower() for v in ["vision", "scout", "maverick"])]
                    v_model = vision_models[0] if vision_models else selected_model
                    
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
                        model=v_model,
                    )
                else:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_content},
                            {"role": "user", "content": user_query}
                        ],
                        model=selected_model,
                    )
                
                ai_reply = chat_completion.choices[0].message.content
                st.markdown(ai_reply)

                c.execute("INSERT INTO chat_logs (username, role, content) VALUES (?, ?, ?)", (username, "assistant", ai_reply))
                conn.commit()
            except Exception as e:
                st.error(f"பிழை: {e}")
            
