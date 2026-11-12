import streamlit as st
import sqlite3
import base64
from io import BytesIO
from pypdf import PdfReader
from PIL import Image
from groq import Groq

st.set_page_config(page_title="Venu AI", page_icon="🎓", layout="wide")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

@st.cache_data(ttl=3600)
def get_models():
    try:
        models = client.models.list()
        all_ids = [m.id for m in models.data if not any(x in m.id.lower() for x in ["whisper", "guard", "tts", "playai"])]
        return all_ids if all_ids else ["gemma2-9b-it"]
    except Exception:
        return ["gemma2-9b-it"]

available_models = get_models()
v_list = [m for m in available_models if any(k in m.lower() for k in ["scout", "maverick", "vision"])]
vision_model = v_list[0] if v_list else available_models[0]

t_list = [m for m in available_models if any(k in m.lower() for k in ["llama-3.3", "llama-3.1", "gemma2"])]
text_model = t_list[0] if t_list else available_models[0]

conn = sqlite3.connect("venu_subjects.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS subject_chats (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, subject TEXT, role TEXT, content TEXT, file_name TEXT)")
conn.commit()

if "active_subject" not in st.session_state:
    st.session_state.active_subject = "Physics"

with st.sidebar:
    st.title("⚙️ Venu AI Settings")
    username = st.text_input("உங்கள் பெயர்:", value="Venugopal").strip().lower()
    selected_model = st.selectbox("AI Model:", available_models, index=available_models.index(text_model))
    st.divider()
    if st.button("🗑️ History-ஐ அழி"):
        c.execute("DELETE FROM subject_chats WHERE username = ? AND subject = ?", (username, st.session_state.active_subject))
        conn.commit()
        st.rerun()

st.markdown("<h1 style='text-align: center;'>🎓 Venu AI</h1>", unsafe_allow_html=True)

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
st.subheader(f"📂 {current_sub} (Question Papers & Answers)")

c.execute("SELECT DISTINCT file_name FROM subject_chats WHERE username = ? AND subject = ? AND file_name != ''", (username, current_sub))
saved_files = [row[0] for row in c.fetchall()]
if saved_files:
    st.caption("📌 சேமிக்கப்பட்டவை: " + ", ".join(saved_files))

st.divider()

c.execute("SELECT role, content, file_name FROM subject_chats WHERE username = ? AND subject = ?", (username, current_sub))
for role, content, f_name in c.fetchall():
    with st.chat_message(role):
        if f_name:
            st.info(f"📄 File: {f_name}")
        st.markdown(content)

prompt_data = st.chat_input(f"{current_sub} கொஸ்டின் பேப்பரை (+) அழுத்தி அப்லோட் செய்யவும்...", accept_file=True, file_type=["pdf", "txt", "jpg", "jpeg", "png"])

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
            st.info(f"📄 அப்லோட் ஆனது: {uploaded_file_name}")
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

    c.execute("INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)", (username, current_sub, "user", user_query, uploaded_file_name))
    conn.commit()

    sub_prompt = f"நீங்கள் 12-ம் வகுப்பு {current_sub} ஆசிரியர். கொடுக்கப்பட்டுள்ள கேள்விகளுக்குத் தெளிவான விடைகளைத் தாருங்கள்.\nDocument: {file_text[:18000]}"

    with st.chat_message("assistant"):
        with st.spinner("விடைகளைத் தயாரிக்கிறது..."):
            try:
                if base64_image:
                    msg = [{"role": "user", "content": [{"type": "text", "text": f"{sub_prompt}\n\nகேள்வி: {user_query}"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]
                    res = client.chat.completions.create(messages=msg, model=vision_model)
                else:
                    msg = [{"role": "system", "content": str(sub_prompt)}, {"role": "user", "content": str(user_query)}]
                    res = client.chat.completions.create(messages=msg, model=selected_model)
                
                ai_reply = res.choices[0].message.content
                st.markdown(ai_reply)
                c.execute("INSERT INTO subject_chats (username, subject, role, content, file_name) VALUES (?, ?, ?, ?, ?)", (username, current_sub, "assistant", ai_reply, ""))
                conn.commit()
            except Exception as e:
                st.error(f"பிழை: {e}")
# END OF CODE
