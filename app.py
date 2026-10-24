import streamlit as st
from groq import Groq
from agents import get_agent_prompt

st.set_page_config(
    page_title="VENU AI ULTIMATE",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 VENU AI ULTIMATE")
st.caption("Your Personal Multi-Agent AI Assistant")

with st.sidebar:
    st.header("⚙️ Settings")
    agent = st.selectbox(
        "Choose AI Agent",
        [
            "Master Agent",
            "Coding Agent",
            "Study Agent",
            "Writing Agent",
            "Task Agent"
        ]
    )

    api_key = st.text_input(
        "Groq API Key",
        type="password"
    )

    st.caption("API Key-ஐ GitHub-ல் சேமிக்காதே.")

if "history" not in st.session_state:
    st.session_state.history = []

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("தமிழில் கேள்வி கேள்...")

if question:
    st.session_state.history.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.write(question)

    if not api_key:
        st.warning("முதலில் Groq API Key உள்ளிடவும்.")
    else:
        try:
            client = Groq(api_key=api_key)

            messages = [
                {
                    "role": "system",
                    "content": get_agent_prompt(agent)
                }
            ]

            messages.extend(st.session_state.history[-10:])

            with st.chat_message("assistant"):
                with st.spinner("VENU AI யோசிக்கிறது..."):
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=messages
                    )

                    answer = response.choices[0].message.content
                    st.markdown(answer)

            st.session_state.history.append(
                {"role": "assistant", "content": answer}
            )

        except Exception as e:
            st.error(f"பிழை ஏற்பட்டது: {e}")
