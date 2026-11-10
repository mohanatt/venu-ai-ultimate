from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import streamlit as st
from streamlit.components.v1 import html as component_html

from agents import DEFAULT_GROQ_MODEL_ID, MasterAgent


st.set_page_config(
    page_title="VENU AI ULTIMATE",
    page_icon="🤖",
    layout="wide",
)


def get_secret(name: str, default: str = "") -> str:
    """Read a value from Streamlit Secrets or environment variables."""
    try:
        if hasattr(st, "secrets") and name in st.secrets:
            value = st.secrets.get(name)
            if value is not None:
                return str(value).strip()
    except Exception:
        pass

    env_value = os.getenv(name, default)
    return str(env_value).strip() if env_value is not None else ""


def get_groq_api_key() -> str:
    return get_secret("GROQ_API_KEY")


def get_groq_model_id() -> str:
    return get_secret("GROQ_MODEL_ID", DEFAULT_GROQ_MODEL_ID)


def get_tavily_api_key() -> str:
    return get_secret("TAVILY_API_KEY")


def clean_markdown_for_speech(text: str) -> str:
    """Remove markdown symbols and code blocks so audio speaks naturally."""
    clean = re.sub(r"```[\s\S]*?```", " Code snippet provided. ", text)
    clean = re.sub(r"`.*?`", "", clean)
    clean = re.sub(r"[#*_~>\[\]\(\)]", " ", clean)
    return " ".join(clean.split())


def initialize_app_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "வணக்கம்! 👋 நான் VENU AI.\n\n"
                    "உனக்கு படிப்பு, Coding, Internet Search, "
                    "மற்றும் குரல் உதவி போன்ற விஷயங்களில் உதவ முடியும்.\n\n"
                    "என்ன கேட்க விரும்புகிறாய்?"
                ),
            }
        ]

    if "voice_enabled" not in st.session_state:
        st.session_state.voice_enabled = True

    if "pending_speech" not in st.session_state:
        st.session_state.pending_speech = ""

    if "last_voice_transcript" not in st.session_state:
        st.session_state.last_voice_transcript = ""


def build_sidebar() -> str:
    st.sidebar.title("🤖 VENU AI ULTIMATE")
    st.sidebar.caption("Personal AI Assistant | Tamil Nadu")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✨ Features")
    st.sidebar.markdown(
        """
        - 🎙️ Voice Input (Web Speech API)
        - 🔊 Text to Speech (Tamil & English)
        - 🌐 Internet Search (Tavily)
        - 💻 Coding Specialist
        - 📚 Study Assistant
        """
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Choose AI Agent")
    selected_agent = st.sidebar.selectbox(
        "Select an agent",
        [
            "Master Agent",
            "Internet Search Agent",
            "Coding Agent",
            "Study Agent",
        ],
        key="selected_agent",
    )

    st.sidebar.markdown("---")
    st.sidebar.checkbox(
        "🔊 Voice Assistant (Speech Output)",
        value=st.session_state.get("voice_enabled", True),
        key="voice_enabled",
    )

    st.sidebar.caption(f"Groq Model: `{get_groq_model_id()}`")

    if get_tavily_api_key():
        st.sidebar.caption("🟢 Tavily Search: Active")
    else:
        st.sidebar.caption("⚪ Tavily Search: Not Configured")

    if st.sidebar.button("🛑 Stop Speaking"):
        st.session_state.pending_speech = ""
        st.rerun()

    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "வணக்கம்! நான் VENU AI. என்ன உதவி வேண்டும்?",
            }
        ]
        st.session_state.pending_speech = ""
        st.rerun()

    return selected_agent


def render_search_results(results: List[Dict[str, Any]]) -> None:
    if not results:
        return

    with st.expander("🌐 Internet Search Results", expanded=False):
        for index, result in enumerate(results, start=1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get("snippet", "No summary available.")
            date_value = result.get("date", "Date not available")

            st.markdown(f"**{index}. {title}**")
            if url:
                st.markdown(f"[🔗 Open Link]({url})")
            if snippet:
                st.caption(snippet)
            st.caption(f"📅 {date_value}")
            st.markdown("---")


def initialize_agent() -> None:
    if "master_agent" in st.session_state:
        return

    groq_key = get_groq_api_key()
    if not groq_key:
        st.error("⚠️ GROQ_API_KEY is missing. Add it in Streamlit Secrets or Environment.")
        st.code(
            'GROQ_API_KEY = "gsk_..."\n'
            'GROQ_MODEL_ID = "llama-3.3-70b-versatile"\n'
            'TAVILY_API_KEY = "tvly-..."',
            language="toml",
        )
        st.stop()

    try:
        st.session_state.master_agent = MasterAgent(
            api_key=groq_key,
            model=get_groq_model_id(),
            search_api_key=get_tavily_api_key(),
        )
    except Exception as exc:
        st.error(f"AI Initialization Failed: {exc}")
        st.stop()


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def process_prompt(prompt_text: str, selected_agent: str) -> None:
    prompt = str(prompt_text).strip()
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    history = st.session_state.messages[:-1]
    agent: MasterAgent = st.session_state.master_agent

    with st.chat_message("assistant"):
        with st.spinner("VENU AI பதில் உருவாக்குகிறது..."):
            try:
                if selected_agent == "Internet Search Agent":
                    response = agent.handle_internet_search(prompt, history=history)
                elif selected_agent == "Coding Agent":
                    response = agent.handle_coding(prompt, history=history)
                elif selected_agent == "Study Agent":
                    response = agent.handle_study(prompt, history=history)
                else:
                    response = agent.handle(prompt, history=history)

                answer = response.get("answer", "பதில் உருவாக்க முடியவில்லை.")
                st.markdown(answer)

                if response.get("used_internet_search"):
                    render_search_results(response.get("search_results", []))

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

                if st.session_state.get("voice_enabled", True):
                    st.session_state.pending_speech = clean_markdown_for_speech(answer)

            except Exception as exc:
                error_message = f"பதில் உருவாக்கும்போது பிழை ஏற்பட்டது: {exc}"
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )
                st.session_state.pending_speech = ""


def render_voice_assistant() -> None:
    if not st.session_state.get("voice_enabled", True):
        return

    speech_text = st.session_state.get("pending_speech", "")
    speech_text_json = json.dumps(speech_text)

    html = f"""
    <div style="margin: 10px 0; padding: 12px; border-radius: 12px; background: #1e293b; color: white; display: flex; align-items: center; justify-content: space-between;">
      <span id="voice-status" style="font-size: 14px; font-weight: 500;">🔊 Voice Assistant Active</span>
      <div>
        <button id="stop-btn" style="border: none; border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: bold; background: #ef4444; color: white; cursor: pointer;">🛑 Stop Voice</button>
      </div>
    </div>
    <script>
      const statusEl = document.getElementById('voice-status');
      const stopBtn = document.getElementById('stop-btn');
      const speechText = {speech_text_json};

      function stopSpeech() {{
        if ('speechSynthesis' in window) {{
          window.speechSynthesis.cancel();
        }}
      }}

      if (speechText && speechText.trim().length > 0) {{
        stopSpeech();
        const utterance = new SpeechSynthesisUtterance(speechText);
        utterance.lang = /[\u0B80-\u0BFF]/.test(speechText) ? 'ta-IN' : 'en-IN';
        utterance.rate = 1.0;
        utterance.onstart = () => {{
          statusEl.textContent = 'Speaking...';
        }};
        utterance.onend = () => {{
          statusEl.textContent = 'Voice Assistant Ready';
        }};
        utterance.onerror = () => {{
          statusEl.textContent = 'Voice playback error';
        }};
        window.speechSynthesis.speak(utterance);
      }}

      stopBtn.addEventListener('click', () => {{
        stopSpeech();
        statusEl.textContent = 'Voice Stopped';
      }});
    </script>
    """
    component_html(html, height=75)


def main() -> None:
    initialize_app_state()
    initialize_agent()
    selected_agent = build_sidebar()

    st.title("🤖 VENU AI ULTIMATE")
    st.caption("Your Personal Multi-Agent AI Assistant | தமிழ் + English")
    st.markdown("---")

    render_voice_assistant()
    render_chat_history()

    prompt = st.chat_input("உங்கள் கேள்வியை உள்ளிடவும்... / Ask your question...")
    if prompt:
        process_prompt(prompt, selected_agent)
        st.rerun()


if __name__ == "__main__":
    main()
