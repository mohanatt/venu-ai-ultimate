import streamlit as st
import sqlite3
import base64
from io import BytesIO
from pypdf import PdfReader
from PIL import Image
from groq import Groq

st.set_page_config(page_title="Venu AI", page_icon="🎓", layout="wide")

# API Key
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# வேலை செய்யும் மாடல்களைத் தானாக எடுத்தல் (404 Error வராமல் இருக்க)
@st.cache_data(ttl=3600)
def get_models():
    try:
        models = client.models.list()
        all_ids = [
            m.id for m in models.data 
            if not any(x in m.id.lower() for x in ["whisper", "guard", "tts", "playai"])
        ]
        return all_ids if all_ids else ["gemma2-9b-it"]
    except Exception:
        return ["gemma2-9b-it"]

available_models = get_models()
vision_candidates = [m for m in available_models if any(k in m.lower() for k in ["scout", "maverick", "vision"])]
vision_model = vision_candidates[0] if vision_candidates else available_models[0]

# preferred text model
text_candidates = [m for m in available_models if any(k in m.lower() for k in ["llama-3.3", "llama-3.1", "gemma2", "qwen"])]
text_model = text_candidates[0] if text_candidates else available_models[0]

# --- Database: Physics, Maths, Chemistry எனத் தனித்தனியாக சேமிக்க ---
conn = sqlite3.connect("venu_subjects.db", check_same_thread=False)
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

# Default Subject Session
if "active_subject" not in st.session_state:
    st.session_state.active_subject = "Physics"

# --- Sidebar (User & Model Settings) ---
with st.sidebar:
    st.title("⚙️ Venu AI Settings")
    username = st.text_input("உங்கள் பெயர்:", value="Venugopal").strip().lower()
    selected_model = st.selectbox("AI Model:", available_models, index=available_models.index(text_model))
    
    st.divider()
    if st.button(f"🗑️ {st.session_state.active_subject} History-ஐ மட்டும் அழி"):
        c.execute("DELETE FROM subject_chats WHERE username = ? AND subject = ?", (username, st.session_state.active_subject))
        conn.commit()
        st.rerun()

# --- 1. Top Title: Venu AI ---
st.markdown("<h1 style='text-align: center;'>🎓 Venu AI</h1>", unsafe_allow_html=True)

# --- 2. Subject Boxes: Physics | Maths | Chemistry (தனித்தனி பிரிவுகள்) ---
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
st.subheader(f"📂 {current_sub} Section (Question Papers & Answers)")

# அந்தந்த சப்ஜெக்ட்டில் இதுவரை அப்லோட் செய்த Question Papers பட்டியல்
c.execute("SELECT DISTINCT file_name FROM subject_chats WHERE username = ? AND subject = ? AND file_name != ''", (username, current_sub))
saved_files = [row[0] for row in c.fetchall()]
if saved_files:
    st.caption(f"📌 **{current_sub}-ல் சேமிக்கப்பட்ட Question Papers:** " + ", ".join(saved_files))

st.divider()

# --- 3. தேர்ந்தெடுத்த சப்ஜெக்ட்டின் பழைய Question Paper & Answers மட்டும் காட்டுதல் ---
c.execute("SELECT role, content, file_name FROM subject_chats WHERE username = ? AND subject = ?", (username, current_sub))
sub_history = c.fetchall()

for role, content, f_name in sub_history:
    with st.chat_message(role):
        if f_name:
            st.info(f"📄 File: {f_name}")
        st.markdown(content)

# --- 4. கீழே + Upload மற்றும் Send Box ---
prompt_data = st.chat_input(
    f"{current_sub} கொஸ்டின் பேப்பரை (+) அழுத்தி அப்லோட் செய்யவும் அல்லது கேள்வி கேட்கவும்...",
    accept_file=True,
    file_type=["pdf", "txt", "jpg", "jpeg", "png"]
)

if prompt_data:
    user_query = prompt_data.text or f"இந்த {current_sub} கொஸ்டின் பேப்பரில் உள்ள அனைத்து கேள்விகளுக்கும் தெளிவாக விடை (Generate Answers) எழுதித் தரவும்."
    uploaded_files = prompt_data.files

    file_text = ""
    uploaded_file_name = ""
    base64_image = None

    with st.chat_message("user"):
        if uploaded_files:
            u_file = uploaded_files[0]
            uploaded_file_name = u_file.name
            st.info(f"📄 அப்லோட் ஆனது ({current_sub}): {uploaded_file_name}")
            
            if u_file.type == "application/pdf":
                reader = PdfReader(u_file)
                for page in reader.pages:
                    file_text += page.extract_text() or ""
            elif u_file.type == "text/plain":
                file_text = u_file.read().decode("utf-8")
            elif u_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                img = Image.open(u_file)
                st.image(img, width=280)
                img.thumbnail((1024, 1024))
                buffered = BytesIO()
                img.convert("RGB").save(buffered, format="JPEG", quality=85)
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        st.markdown(user_query)

    # கேள்வியை அந்த சப்ஜெக்ட் பாக்ஸில் சேமித்தல்
    c.execute(
        "INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)",
        (username, current_sub, "user", user_query, uploaded_file_name)
    )
    conn.commit()

    # சப்ஜெக்ட் வாரியான பிரத்யேக AI ஆசிரியர் அறிவுறுத்தல்
    subject_prompt = f"""
    நீங்கள் 12-ம் வகுப்பு {current_sub} பாடத்திற்கான சிறப்பு ஆசிரியர்.
    பயனர் அப்லோட் செய்துள்ள {current_sub} Question Paper அல்லது கேள்வியைப் படித்து, 
    ஒவ்வொரு கேள்விக்கும் தேர்வுக்கு எழுதுவது போலத் தெளிவான Step-by-step விடைகளை (Answers) உருவாக்கவும்.
    
    Question Paper Content:
    {file_text[:18000] if file_text else "டெக்ஸ்ட் ஃபைல் இல்லை."}
    """

    with st.chat_message("assistant"):
        with st.spinner(f"{current_sub} விடைகளைத் தயாரிக்கிறது..."):
            try:
                if base64_image:
                    # போட்டோ கொஸ்டின் பேப்பராக இருந்தால் Vision Model
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"{subject_prompt}\n\nகேள்வி: {user_query}"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                                ],
                            }
                        ],
                        model=vision_model,
                    )
                else:
                    # PDF அல்லது சாதாரண கேள்விக்கு Text Model
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": str(subject_prompt)},
                            {"role": "user", "content": str(user_query)}
                        ],
                        model=selected_model,
                    )
                
                ai_reply = chat_completion.choices[0].message.content
                st.markdown(ai_reply)

                # பதிலையும் அந்தந்த சப்ஜெக்ட் (Physics/Maths/Chemistry) பிரிவிலேயே சேமித்தல்
                c.execute(
                    "INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)",
                    (
                                        
