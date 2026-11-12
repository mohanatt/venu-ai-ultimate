import streamlit as st
import sqlite3
import base64
from io import BytesIO
from pypdf import PdfReader
from PIL import Image
from groq import Groq

st.set_page_config(page_title="Venu AI Ultimate", page_icon="🎓", layout="wide")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

@st.cache_data(ttl=3600)
def get_models():
    try:
        models = client.models.list()
        # ஆடியோ, ஆர்ஃபியூஸ் மற்றும் இதர கட்டுப்பாடுள்ள மாடல்களைத் தவிர்த்து Llama / Gemma / Qwen மட்டும் எடுத்தல்
        chat_models = [
            m.id for m in models.data 
            if not any(x in m.id.lower() for x in ["whisper", "orpheus", "guard", "tts", "playai"])
            and any(k in m.id.lower() for k in ["llama", "gemma", "qwen", "mixtral"])
        ]
        return chat_models if chat_models else ["gemma2-9b-it"]
    except Exception:
        return ["gemma2-9b-it"]

available_models = get_models()

# Vision மாடல் தேர்வு
vision_candidates = [m for m in available_models if any(k in m.lower() for k in ["scout", "maverick", "vision", "llama-4"])]
vision_model = vision_candidates[0] if vision_candidates else available_models[0]

# Text மாடல் தேர்வு
text_candidates = [m for m in available_models if any(k in m.lower() for k in ["llama-3.3", "llama-3.1", "gemma2"])]
text_model = text_candidates[0] if text_candidates else available_models[0]

# --- Database Setup ---
conn = sqlite3.connect("venu_hub.db", check_same_thread=False)
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

# --- Main App ---
st.markdown("<h1 style='text-align: center;'>🎓 Venu AI - Study Hub</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Venu AI Settings")
    username = st.text_input("உங்கள் பெயர்:", value="venugopal").strip().lower()
    selected_model = st.selectbox("AI Model:", available_models, index=available_models.index(text_model) if text_model in available_models else 0)
    
    st.divider()
    if st.button("🗑️ தற்போதைய Subject History-ஐ அழி"):
        c.execute("DELETE FROM subject_chats WHERE username = ? AND subject = ?", (username, st.session_state.active_subject))
        conn.commit()
        st.rerun()

if "active_subject" not in st.session_state:
    st.session_state.active_subject = "Physics"

# Subject Buttons
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
st.subheader(f"📂 {current_sub} Section")

# --- Export Notes as TXT ---
c.execute("SELECT role, content FROM subject_chats WHERE username = ? AND subject = ?", (username, current_sub))
chat_records = c.fetchall()

if chat_records:
    export_text = f"--- Venu AI Study Notes ({current_sub}) ---\nUser: {username}\n\n"
    for r, text in chat_records:
        export_text += f"{r.upper()}:\n{text}\n\n" + "="*40 + "\n\n"
    
    st.download_button(
        label=f"📥 Download {current_sub} Notes (TXT)",
        data=export_text,
        file_name=f"{username}_{current_sub}_notes.txt",
        mime="text/plain"
    )

st.divider()

# Display Chat History
for role, content in chat_records:
    with st.chat_message(role):
        st.markdown(content)

# Chat Input & File Upload
prompt_data = st.chat_input(f"{current_sub} கொஸ்டின் பேப்பரை (+) அப்லோட் செய்யவும்...", accept_file=True, file_type=["pdf", "txt", "jpg", "jpeg", "png"])

if prompt_data:
    user_query = prompt_data.text or f"இந்த {current_sub} கொஸ்டின் பேப்பரில் உள்ள கேள்விகளுக்குத் தெளிவாக விடை எழுதித் தரவும்."
    uploaded_files = prompt_data.files
    file_text = ""
    uploaded_file_name = ""
    base64_image = None

    with st.chat_message("user"):
        if uploaded_files:
            u_file = uploaded_files[0]
            uploaded_file_name = u_file.name
            if u_file.type == "application/pdf":
                reader = PdfReader(u_file)
                for page in reader.pages:
                    file_text += page.extract_text() or ""
                st.info(f"📄 PDF: {uploaded_file_name}")
            elif u_file.type == "text/plain":
                file_text = u_file.read().decode("utf-8")
                st.info(f"📝 Text: {uploaded_file_name}")
            elif u_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                img = Image.open(u_file)
                img.thumbnail((600, 600))
                buffered = BytesIO()
                img.convert("RGB").save(buffered, format="JPEG", quality=50)
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
                st.image(img, width=250)
                st.success("✅ போட்டோ அப்லோட் ஆனது!")
        st.markdown(user_query)

    c.execute("INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)", (username, current_sub, "user", user_query, uploaded_file_name))
    conn.commit()

    sub_prompt = f"நீங்கள் 12-ம் வகுப்பு {current_sub} ஆசிரியர். கொடுக்கப்பட்டுள்ள கொஸ்டின் பேப்பரைப் படித்து கேள்விகளுக்குத் தெளிவான விடைகளைத் தாருங்கள்."

    with st.chat_message("assistant"):
        with st.spinner("AI விடைகளைத் தயாரிக்கிறது..."):
            try:
                if base64_image:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"{sub_prompt}\n\nகேள்வி: {user_query}"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                                ],
                            }
                        ],
                        model=vision_model,
                    )
                else:
                    msg = [
                        {"role": "system", "content": str(sub_prompt + f"\nDocument: {file_text[:15000]}")},
                        {"role": "user", "content": str(user_query)}
                    ]
                    chat_completion = client.chat.completions.create(messages=msg, model=selected_model)
                
                ai_reply = chat_completion.choices[0].message.content
                st.markdown(ai_reply)

                c.execute("INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)", (username, current_sub, "assistant", ai_reply, ""))
                conn.commit()
            except Exception as e:
                st.error(f"பிழை: {e}")
        
