import os
from typing import Any, Dict, List

import streamlit as st

from agents import MasterAgent


def get_groq_api_key() -> str:
    """Read Groq API key securely from Streamlit secrets or environment variables."""
    try:
        value = st.secrets.get("GROQ_API_KEY")
        if value:
            return str(value)
    except Exception:
        pass

    value = os.getenv("GROQ_API_KEY")
    if value:
        return str(value)

    return ""


def build_sidebar() -> None:
    st.sidebar.title("VENU AI ULTIMATE")
    st.sidebar.caption("தமிழ் + English support")
    st.sidebar.markdown(
        """
        - Real internet search with DuckDuckGo
        - Groq-powered multi-agent workflow
        - Current news, coding, and study support
        - Streamlit Community Cloud friendly
        """
    )

    st.sidebar.markdown("### Agent")
    agent = st.selectbox(
        "Choose AI Agent",
        ["Master Agent", "Internet Search Agent", "Coding Agent", "Study Agent"],
    )
    st.session_state.selected_agent = agent

    st.sidebar.markdown("### Groq API Key")
    st.sidebar.code('GROQ_API_KEY = "your_key_here"')
    st.sidebar.caption("Set this in Streamlit Cloud > Settings > Secrets")


def render_search_results(results: List[Dict[str, Any]]) -> None:
    if not results:
        return

    with st.expander("🔎 Internet Search Results", expanded=False):
        for index, result in enumerate(results, start=1):
            title = result.get("title") or "Untitled"
            url = result.get("url") or ""
            snippet = result.get("snippet") or "No summary available."
            date_value = result.get("date") or "Date not available"

            st.markdown(f"### {index}. {title}")
            if url:
                st.markdown(f"Source: [{url}]({url})")
            st.write(snippet)
            if date_value:
                st.caption(f"Date: {date_value}")
            st.markdown("---")


def main() -> None:
    st.set_page_config(
        page_title="VENU AI ULTIMATE",
        page_icon="🤖",
        layout="wide",
    )

    build_sidebar()

    st.title("🤖 VENU AI ULTIMATE")
    st.caption("Your Personal Multi-Agent AI Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I can help with current news, coding, and study questions. Ask in Tamil or English.",
            }
        ]

    if "master_agent" not in st.session_state:
        groq_key = get_groq_api_key()
        if not groq_key:
            st.warning(
                "Groq API key is missing. Add it in Streamlit Secrets or set the GROQ_API_KEY environment variable."
            )
            st.stop()
        st.session_state.master_agent = MasterAgent(api_key=groq_key)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("உங்கள் கேள்வியை உள்ளிடவும்... / Ask your question...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            selected_agent = st.session_state.get("selected_agent", "Master Agent")
            agent = st.session_state.master_agent

            if selected_agent == "Internet Search Agent":
                response = agent.handle_internet_search(prompt)
            elif selected_agent == "Coding Agent":
                response = agent.handle_coding(prompt, history=st.session_state.messages)
            elif selected_agent == "Study Agent":
                response = agent.handle_study(prompt, history=st.session_state.messages)
            else:
                response = agent.handle(prompt, history=st.session_state.messages)

            answer = response.get("answer", "I could not generate a response.")
            results = response.get("search_results", [])

            with st.chat_message("assistant"):
                st.markdown(answer)
                if response.get("used_internet_search"):
                    render_search_results(results)

            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as exc:
            error_message = (
                "I hit an error while processing your request. "
                f"Details: {exc}"
            )
            with st.chat_message("assistant"):
                st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})


if __name__ == "__main__":
    main()
