import streamlit as st
import sqlite3
import base64
from io import BytesIO
from pypdf import PdfReader
from PIL import Image
from groq import Groq

st.set_page_config(page_title="Venu Advanced Study AI", page_icon="🚀", layout="wide")

# API Key Check
try:
    api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    st.error("தயவுசெய்து Streamlit Secrets-ல் GROQ_API_KEY-ஐச் சேர்க்கவும்!")
    st.stop()

client = Groq(api_key=api_key)

@st.cache_data(ttl=3600)
def get_models():
    try:
        models = client.models.list()
        chat_models = [
            m.id for m in models.data 
            if not any(x in m.id.lower() for x in ["whisper", "orpheus", "guard", "tts", "playai"])
            and any(k in m.id.lower() for k in ["llama", "gemma", "qwen", "mixtral"])
        ]
        return chat_models if chat_models else ["gemma2-9b-it"]
    except Exception:
        return ["gemma2-9b-it"]

available_models = get_models()

vision_candidates = [m for m in available_models if any(k in m.lower() for k in ["scout", "maverick", "vision", "llama-4"])]
vision_model = vision_candidates[0] if vision_candidates else available_models[0]

text_candidates = [m for m in available_models if any(k in m.lower() for k in ["llama-3.3", "llama-3.1", "gemma2"])]
text_model = text_candidates[0] if text_candidates else available_models[0]

# --- Database Setup ---
conn = sqlite3.connect("venu_advanced_hub.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS subject_chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        subject TEXT,
        role TEXT,
        content TEXT,
        file_name TEXT
    )
""")
conn.commit()

# --- UI Header ---
st.markdown("<h1 style='text-align: center;'>🚀 Venu Advanced Study AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>12th Bio-Maths | Physics, Maths & Chemistry Expert Assistant</p>", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ AI Control Panel")
    username = st.text_input("மாணவர் பெயர்:", value="venugopal").strip().lower()
    selected_model = st.selectbox("AI Model:", available_models, index=available_models.index(text_model) if text_model in available_models else 0)
    
    st.divider()
    if st.button("🗑️ தற்போதைய Subject History-ஐ அழி"):
        c.execute("DELETE FROM subject_chats WHERE username = ? AND subject = ?", (username, st.session_state.active_subject))
        conn.commit()
        st.rerun()

if "active_subject" not in st.session_state:
    st.session_state.active_subject = "Physics"

# Subject Navigation Buttons[span_2](start_span)[span_2](end_span)
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("⚛️ Physics", use_container_width=True, type="primary" if st.session_state.active_subject == "Physics" else "secondary"):
        st.session_state.active_subject = "Physics"
        st.rerun()
with col2:
    if st.button("📐 Maths", use_container_width=True, type="primary" if st.session_state.active_subject == "Maths" else "secondary"):
        st.session_state.active_subject = "Maths"
        st.rerun()
with col3:
    if st.button("🧪 Chemistry", use_container_width=True, type="primary" if st.session_state.active_subject == "Chemistry" else "secondary"):
        st.session_state.active_subject = "Chemistry"
        st.rerun()

current_sub = st.session_state.active_subject
st.subheader(f"📂 {current_sub} Study Section")

# --- Export Notes as TXT ---
c.execute("SELECT role, content FROM subject_chats WHERE username = ? AND subject = ?", (username, current_sub))
chat_records = c.fetchall()

if chat_records:
    export_text = f"--- Venu Advanced AI Study Notes ({current_sub}) ---\nStudent: {username}\n\n"
    for r, text in chat_records:
        export_text += f"{r.upper()}:\n{text}\n\n" + "="*40 + "\n\n"
    
    st.download_button(
        label=f"📥 Download {current_sub} Notes & Answers (TXT)",
        data=export_text,
        file_name=f"{username}_{current_sub}_advanced_notes.txt",
        mime="text/plain"
    )

st.divider()

# --- Stable File Uploader Box ---
uploaded_file = st.file_uploader(
    f"📂 {current_sub} கொஸ்டின் பேப்பர் அல்லது நோட்ஸ் (PDF / Image) இங்கே அப்லோட் செய்யவும்:",
    type=["pdf", "txt", "jpg", "jpeg", "png"]
)

# Display Chat History
for role, content in chat_records:
    with st.chat_message(role):
        st.markdown(content)

# Quick Action Prompt Buttons
q_col1, q_col2 = st.columns(2)
with q_col1:
    btn_step = st.button("📝 Step-by-step தீர்வு தரு")
with q_col2:
    btn_formula = st.button("📐 முக்கிய சூத்திரங்கள் (Formulas)")

default_query_prefix = ""
if btn_step:
    default_query_prefix = "கொடுக்கப்பட்டுள்ள கேள்விகளுக்கு மிகத் தெளிவான Step-by-step தீர்வுகளைத் தரவும்."
elif btn_formula:
    default_query_prefix = "இந்தத் தலைப்பு அல்லது கேள்விகளுக்குத் தேவையான அனைத்து முக்கிய சூத்திரங்களையும் (Formulas) பட்டியலிடவும்."

# Chat Input
user_query = st.chat_input("உங்கள் சந்தேகத்தைக் கேளுங்கள்...")
final_query = user_query or default_query_prefix

if final_query or uploaded_file:
    query_text = final_query if final_query else f"இந்த {current_sub} ஆவணத்தில் உள்ள கேள்விகளுக்கு விரிவான விடைகளைத் தரவும்."
    
    file_text = ""
    uploaded_file_name = ""
    base64_image = None

    with st.chat_message("user"):
        if uploaded_file is not None:
            uploaded_file_name = uploaded_file.name
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    file_text += page.extract_text() or ""
                st.info(f"📄 PDF Loaded: {uploaded_file_name}")
            elif uploaded_file.type == "text/plain":
                file_text = uploaded_file.read().decode("utf-8")
                st.info(f"📝 Text Loaded: {uploaded_file_name}")
            elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                img = Image.open(uploaded_file)
                img.thumbnail((700, 700))
                buffered = BytesIO()
                img.convert("RGB").save(buffered, format="JPEG", quality=60)
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
                st.image(img, width=280)
                st.success("✅ படம் வெற்றிகரமாக இணைக்கப்பட்டது!")
        
        st.markdown(query_text)

    c.execute("INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)", (username, current_sub, "user", query_text, uploaded_file_name))
    conn.commit()

    sub_prompt = f"""நீங்கள் 12-ம் வகுப்பு Bio-Maths மாணவர்களுக்கான தலைசிறந்த AI ஆசிரியர் ({current_sub} Expert). 
    மாணவர்களுக்குப் புரியும் வகையில் எளிய முறையில், அறிவியல் மற்றும் கணித விதிமுறைகளுடன் துல்லியமான விடைகளைத் தரவும்."""

    with st.chat_message("assistant"):
        with st.spinner("AI சிந்தikus துல்லியமான பதிலைத் தயாரிக்கிறது..."):
            try:
                if base64_image:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"{sub_prompt}\n\nகேள்வி: {query_text}"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                                ],
                            }
                        ],
                        model=vision_model,
                    )
                else:
                    msg = [
                        {"role": "system", "content": str(sub_prompt + f"\nDocument Context: {file_text[:15000]}")},
                        {"role": "user", "content": str(query_text)}
                    ]
                    chat_completion = client.chat.completions.create(messages=msg, model=selected_model)
                
                ai_reply = chat_completion.choices[0].message.content
                st.markdown(ai_reply)

                c.execute("INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)", (username, current_sub, "assistant", ai_reply, ""))
                conn.commit()
            except Exception as e:
                st.error(f"பிழை ஏற்பட்டுள்ளது: {e}")
    
