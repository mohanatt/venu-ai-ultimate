from __future__ import annotations

import os
from typing import Any, Dict, List

import streamlit as st

from agents import DEFAULT_GROQ_MODEL_ID, MasterAgent


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="VENU AI ULTIMATE",
    page_icon="🤖",
    layout="wide",
)


# --------------------------------------------------
# SECRETS
# --------------------------------------------------

def get_secret(name: str, default: str = "") -> str:
    """Read a value from Streamlit Secrets or environment variables."""
    try:
        value = st.secrets.get(name)

        if value:
            return str(value).strip()

    except Exception:
        pass

    return os.getenv(name, default).strip()


def get_groq_api_key() -> str:
    return get_secret("GROQ_API_KEY")


def get_groq_model_id() -> str:
    return get_secret(
        "GROQ_MODEL_ID",
        DEFAULT_GROQ_MODEL_ID,
    )


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

def build_sidebar() -> str:
    st.sidebar.title("🤖 VENU AI ULTIMATE")
    st.sidebar.caption("Your Personal Multi-Agent AI Assistant")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✨ Features")

    st.sidebar.markdown(
        """
        - 🌐 Internet Search
        - 📰 Current information
        - 💻 Coding assistance
        - 📚 Study assistance
        - 🇮🇳 Tamil + English
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
    st.sidebar.caption(
        f"Groq Model: {get_groq_model_id()}"
    )

    st.sidebar.info(
        "API keys are stored in Streamlit Secrets. "
        "Never share them publicly."
    )

    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "வணக்கம்! நான் VENU AI. "
                    "என்ன உதவி வேண்டும்?"
                ),
            }
        ]

        st.rerun()

    return selected_agent


# --------------------------------------------------
# SEARCH RESULTS
# --------------------------------------------------

def render_search_results(
    results: List[Dict[str, Any]],
) -> None:
    if not results:
        return

    with st.expander(
        "🌐 Internet Search Results",
        expanded=True,
    ):
        for index, result in enumerate(
            results,
            start=1,
        ):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get(
                "snippet",
                "No summary available.",
            )
            date_value = result.get(
                "date",
                "Date not available",
            )

            st.markdown(f"### {index}. {title}")

            if url:
                st.markdown(f"[🔗 Open Source]({url})")

            if snippet:
                st.write(snippet)

            st.caption(f"Date: {date_value}")
            st.markdown("---")


# --------------------------------------------------
# AGENT INITIALIZATION
# --------------------------------------------------

def initialize_agent() -> None:
    if "master_agent" in st.session_state:
        return

    groq_key = get_groq_api_key()

    if not groq_key:
        st.error(
            "GROQ_API_KEY கிடைக்கவில்லை. "
            "Streamlit Secrets பகுதியில் API Key சேர்க்கவும்."
        )

        st.code(
            'GROQ_API_KEY = "your_groq_api_key"\n'
            'GROQ_MODEL_ID = "openai/gpt-oss-20b"\n'
            'TAVILY_API_KEY = "your_tavily_api_key"',
            language="toml",
        )

        st.stop()

    model_id = get_groq_model_id()

    try:
        st.session_state.master_agent = MasterAgent(
            api_key=groq_key,
            model=model_id,
        )

    except Exception as exc:
        st.error(
            f"AI initialization failed: {exc}"
        )
        st.stop()


# --------------------------------------------------
# CHAT
# --------------------------------------------------

def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def process_prompt(
    prompt: str,
    selected_agent: str,
) -> None:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    history = st.session_state.messages[:-1]
    agent = st.session_state.master_agent

    with st.chat_message("assistant"):
        with st.spinner("VENU AI பதில் உருவாக்குகிறது..."):
            try:
                if selected_agent == "Internet Search Agent":
                    response = agent.handle_internet_search(
                        prompt
                    )

                elif selected_agent == "Coding Agent":
                    response = agent.handle_coding(
                        prompt,
                        history=history,
                    )

                elif selected_agent == "Study Agent":
                    response = agent.handle_study(
                        prompt,
                        history=history,
                    )

                else:
                    response = agent.handle(
                        prompt,
                        history=history,
                    )

                answer = response.get(
                    "answer",
                    "பதில் உருவாக்க முடியவில்லை.",
                )

                st.markdown(answer)

                if response.get("used_internet_search"):
                    render_search_results(
                        response.get("search_results", [])
                    )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            except Exception as exc:
                error_message = (
                    "பதில் உருவாக்கும்போது பிழை ஏற்பட்டது.\n\n"
                    f"விவரம்: {exc}"
                )

                st.error(error_message)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )


# --------------------------------------------------
# MAIN APP
# --------------------------------------------------

def main() -> None:
    selected_agent = build_sidebar()

    st.title("🤖 VENU AI ULTIMATE")

    st.caption(
        "Your Personal Multi-Agent AI Assistant | "
        "தமிழ் + English"
    )

    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "வணக்கம்! 👋 நான் VENU AI.\n\n"
                    "உனக்கு படிப்பு, Coding, Internet Search "
                    "போன்ற விஷயங்களில் உதவ முடியும்.\n\n"
                    "என்ன கேட்க விரும்புகிறாய்?"
                ),
            }
        ]

    initialize_agent()

    render_chat_history()

    prompt = st.chat_input(
        "உங்கள் கேள்வியை உள்ளிடவும்... / Ask your question..."
    )

    if prompt:
        process_prompt(
            prompt,
            selected_agent,
        )


if __name__ == "__main__":
    main()
