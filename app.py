from __future__ import annotations

import json
import os
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
        if hasattr(st, "secrets"):
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

    if "last_speech_done" not in st.session_state:
        st.session_state.last_speech_done = False


def build_sidebar() -> str:
    st.sidebar.title("🤖 VENU AI ULTIMATE")
    st.sidebar.caption("Siri-style Android voice assistant")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✨ Features")
    st.sidebar.markdown(
        """
        - 🎙️ Voice input (Tamil + English)
        - 🔊 Text to speech
        - 🌐 Internet Search
        - 💻 Coding assistance
        - 📚 Study assistance
        - 🇮🇳 Mobile-first UI
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
        "🔊 Voice assistant on",
        value=st.session_state.get("voice_enabled", True),
        key="voice_enabled",
    )

    st.sidebar.caption(f"Groq Model: {get_groq_model_id()}")

    if get_tavily_api_key():
        st.sidebar.caption("Tavily API: configured")
    else:
        st.sidebar.caption("Tavily API: not configured")

    st.sidebar.info(
        "API keys are stored in Streamlit Secrets. Never share them publicly."
    )

    if st.sidebar.button("🛑 Stop Speaking"):
        st.session_state.pending_speech = ""
        st.session_state.last_speech_done = False

    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": ("வணக்கம்! நான் VENU AI. என்ன உதவி வேண்டும்?"),
            }
        ]
        st.session_state.pending_speech = ""
        st.rerun()

    return selected_agent


def render_search_results(results: List[Dict[str, Any]]) -> None:
    if not results:
        return

    with st.expander("🌐 Internet Search Results", expanded=True):
        for index, result in enumerate(results, start=1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get("snippet", "No summary available.")
            date_value = result.get("date", "Date not available")

            st.markdown(f"### {index}. {title}")
            if url:
                st.markdown(f"[🔗 Open Source]({url})")
            if snippet:
                st.write(snippet)
            st.caption(f"Date: {date_value}")
            st.markdown("---")


def initialize_agent() -> None:
    if "master_agent" in st.session_state:
        return

    groq_key = get_groq_api_key()
    if not groq_key:
        st.error("GROQ_API_KEY is missing. Add it in Streamlit Secrets.")
        st.code(
            'GROQ_API_KEY = "your_groq_api_key"\n'
            'GROQ_MODEL_ID = "openai/gpt-oss-20b"\n'
            'TAVILY_API_KEY = "your_tavily_api_key"',
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
        st.error(f"AI initialization failed: {exc}")
        st.stop()


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def process_prompt(prompts: str, selected_agent: str) -> None:
    prompt = str(prompts).strip()
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    history = st.session_state.messages[:-1]
    agent = st.session_state.master_agent

    with st.chat_message("assistant"):
        with st.spinner("VENU AI பதில் உருவாக்குகிறது..."):
            try:
                if selected_agent == "Internet Search Agent":
                    response = agent.handle_internet_search(prompt)
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
                st.session_state.pending_speech = answer
                st.session_state.last_speech_done = False

            except Exception as exc:
                error_message = (
                    "பதில் உருவாக்கும்போது பிழை ஏற்பட்டது.\n\n"
                    f"விவரம்: {exc}"
                )
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )
                st.session_state.pending_speech = ""


def render_voice_assistant() -> Dict[str, Any]:
    if not st.session_state.get("voice_enabled", True):
        st.info("Voice assistant is turned off. Use text input or enable voice in the sidebar.")
        return {}

    speech_text_json = json.dumps(st.session_state.get("pending_speech", ""))
    voice_enabled_str = str(st.session_state.get("voice_enabled", True)).lower()

    html = """
    <div style="max-width: 520px; margin: 0 auto; padding: 14px; border-radius: 18px; background: linear-gradient(135deg, #0f172a, #1d4ed8); box-shadow: 0 8px 24px rgba(0,0,0,0.25);">
      <div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center; align-items:center;">
        <button id="voice-btn" style="border:none; border-radius:999px; padding:14px 18px; font-size:16px; font-weight:700; background:#f8fafc; color:#0f172a; cursor:pointer; min-width:180px;">🎙️ Voice Input</button>
        <button id="stop-btn" style="border:none; border-radius:999px; padding:14px 18px; font-size:16px; font-weight:700; background:#ef4444; color:white; cursor:pointer;">🛑 Stop Speaking</button>
      </div>
      <div id="voice-status" style="margin-top:12px; text-align:center; color:#e2e8f0; font-size:13px; font-weight:600; min-height:18px;">Voice assistant ready</div>
    </div>
    <script>
      const statusEl = document.getElementById('voice-status');
      const voiceBtn = document.getElementById('voice-btn');
      const stopBtn = document.getElementById('stop-btn');
      const speechText = %s;
      const voiceEnabled = %s;

      function setStatus(message) {
        statusEl.textContent = message;
      }

      function stopSpeech() {
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }
      }

      if (speechText && voiceEnabled) {
        stopSpeech();
        const utterance = new SpeechSynthesisUtterance(speechText);
        utterance.lang = /[\u0B80-\u0BFF]/.test(speechText) ? 'ta-IN' : 'en-IN';
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.onstart = () => setStatus('Speaking...');
        utterance.onend = () => {
          setStatus('Voice assistant ready');
          Streamlit.setComponentValue({ speech_done: true });
        };
        window.speechSynthesis.speak(utterance);
      }

      function startVoiceRecognition(index = 0) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          setStatus('Speech recognition is not supported in this browser.');
          return;
        }

        const recognition = new SpeechRecognition();
        const langList = ['ta-IN', 'en-IN'];
        recognition.lang = langList[index] || 'en-IN';
        recognition.interimResults = false;
        recognition.continuous = false;

        recognition.onstart = () => {
          setStatus('Listening...');
          voiceBtn.textContent = '🎙️ Listening';
        };

        recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript.trim();
          if (transcript) {
            setStatus('Captured: ' + transcript);
            Streamlit.setComponentValue({ transcript: transcript });
          }
        };

        recognition.onerror = (event) => {
          if (index < langList.length - 1) {
            startVoiceRecognition(index + 1);
          } else {
            setStatus('Voice capture failed: ' + event.error);
            voiceBtn.textContent = '🎙️ Voice Input';
          }
        };

        recognition.onend = () => {
          voiceBtn.textContent = '🎙️ Voice Input';
          if (!statusEl.textContent.includes('Captured:')) {
            setStatus('Voice assistant ready');
          }
        };

        recognition.start();
      }

      voiceBtn.addEventListener('click', () => {
        if (!voiceEnabled) {
          setStatus('Voice is switched off from the sidebar.');
          return;
        }
        startVoiceRecognition(0);
      });

      stopBtn.addEventListener('click', () => {
        stopSpeech();
        setStatus('Speaking stopped');
        Streamlit.setComponentValue({ speech_done: true });
      });
    </script>
    """ % (speech_text_json, voice_enabled_str)

    component_value = component_html(html, height=150, key="voice_component")
    return component_value if isinstance(component_value, dict) else {}


def main() -> None:
    initialize_app_state()
    selected_agent = build_sidebar()

    st.title("🤖 VENU AI ULTIMATE")
    st.caption("Your Personal Multi-Agent AI Assistant | தமிழ் + English")
    st.markdown("---")

    voice_result = render_voice_assistant()
    if isinstance(voice_result, dict):
        transcript = str(voice_result.get("transcript", "")).strip()
        speech_done = bool(voice_result.get("speech_done"))

        if transcript and transcript != st.session_state.get("last_voice_transcript"):
            st.session_state.last_voice_transcript = transcript
            process_prompt(transcript, selected_agent)

        if speech_done:
            st.session_state.pending_speech = ""
            st.session_state.last_speech_done = True

    render_chat_history()

    prompt = st.chat_input("உங்கள் கேள்வியை உள்ளிடவும்... / Ask your question...")
    if prompt:
        process_prompt(prompt, selected_agent)

    initialize_agent()


if __name__ == "__main__":
    main()
