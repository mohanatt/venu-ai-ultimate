from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import streamlit as st
from groq import Groq
from tavily import TavilyClient


SUPPORTED_GROQ_MODELS = {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
}

DEFAULT_GROQ_MODEL_ID = "openai/gpt-oss-20b"


def get_secret(name: str) -> str:
    """Read a secret from Streamlit or environment variables."""
    try:
        value = st.secrets.get(name)
        if value:
            return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, "").strip()


def resolve_model_id(model: Optional[str] = None) -> str:
    candidate = (
        model or get_secret("GROQ_MODEL_ID") or DEFAULT_GROQ_MODEL_ID
    ).strip()

    if candidate in SUPPORTED_GROQ_MODELS:
        return candidate

    return DEFAULT_GROQ_MODEL_ID


class GroqAgent:
    """Groq-powered AI assistant."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or get_secret("GROQ_API_KEY")
        self.model = resolve_model_id(model)
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def generate(
        self,
        user_prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not self.client:
            raise ValueError(
                "GROQ_API_KEY missing. Add it in Streamlit Secrets."
            )

        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for item in history[-10:]:
                role = item.get("role")
                content = item.get("content")

                if role in {"user", "assistant"} and content:
                    messages.append({
                        "role": role,
                        "content": content,
                    })

        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5,
            max_tokens=1200,
        )

        return (response.choices[0].message.content or "").strip()


class InternetSearchAgent:
    """Search the web using Tavily."""

    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.api_key = get_secret("TAVILY_API_KEY")

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        if not self.api_key:
            raise RuntimeError(
                "TAVILY_API_KEY missing. Add it in Streamlit Secrets."
            )

        client = TavilyClient(api_key=self.api_key)

        response = client.search(
            query=query,
            topic="general",
            search_depth="basic",
            max_results=max_results or self.max_results,
        )

        results = []

        for item in response.get("results", []):
            url = (item.get("url") or "").strip()

            if not url:
                continue

            results.append({
                "title": item.get("title") or "Untitled",
                "url": url,
                "snippet": item.get("content") or "",
                "date": (
                    item.get("published_date")
                    or "Date not available"
                ),
            })

        return results


class CodingAgent(GroqAgent):
    def answer(self, question, history=None):
        return self.generate(
            question,
            "You are an expert coding assistant. Explain code clearly. "
            "Use simple Tamil when appropriate.",
            history,
        )


class StudyAgent(GroqAgent):
    def explain(self, topic, history=None):
        return self.generate(
            topic,
            "You are a patient tutor. Explain subjects in simple Tamil "
            "with examples and step-by-step instructions.",
            history,
        )


class MasterAgent:
    """Coordinates AI responses and Internet Search."""

    def __init__(self, api_key=None, model=None):
        self.groq_agent = GroqAgent(api_key, model)
        self.search_agent = InternetSearchAgent()
        self.coding_agent = CodingAgent(api_key, model)
        self.study_agent = StudyAgent(api_key, model)

    def handle_internet_search(self, query):
        try:
            results = self.search_agent.search(query, max_results=5)

            if not results:
                return {
                    "answer": "தேடலுக்கான முடிவுகள் கிடைக்கவில்லை.",
                    "search_results": [],
                    "used_internet_search": True,
                }

            context = "\n\n".join(
                f"Title: {r['title']}\n"
                f"URL: {r['url']}\n"
                f"Information: {r['snippet']}"
                for r in results
            )

            answer = self.groq_agent.generate(
                user_prompt

