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


def get_secret(name: str, default: str = "") -> str:
    """Read secrets from Streamlit or environment variables."""
    try:
        if hasattr(st, "secrets"):
            value = st.secrets.get(name)
            if value is not None:
                return str(value).strip()
    except Exception:
        pass

    env_value = os.getenv(name, default)
    return str(env_value).strip() if env_value is not None else ""


def resolve_model_id(model: Optional[str] = None) -> str:
    candidate = (
        model or get_secret("GROQ_MODEL_ID", DEFAULT_GROQ_MODEL_ID)
    ).strip()

    if not candidate:
        return DEFAULT_GROQ_MODEL_ID

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
        self.api_key = (api_key or get_secret("GROQ_API_KEY")).strip()
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

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        if history:
            for item in history[-10:]:
                role = item.get("role")
                content = item.get("content")

                if role in {"user", "assistant"} and content:
                    messages.append({
                        "role": role,
                        "content": str(content),
                    })

        messages.append({
            "role": "user",
            "content": str(user_prompt),
        })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5,
            max_tokens=1200,
        )

        choice = response.choices[0]
        message = getattr(choice, "message", None)
        content = getattr(message, "content", "") or ""

        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )

        return str(content).strip()


class InternetSearchAgent:
    """Search the internet using Tavily."""

    def __init__(self, api_key: Optional[str] = None, max_results: int = 5):
        self.api_key = (api_key or get_secret("TAVILY_API_KEY")).strip()
        self.max_results = max_results

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        if not self.api_key:
            raise RuntimeError(
                "TAVILY_API_KEY missing. Add it in Streamlit Secrets."
            )

        query_text = str(query or "").strip()
        if not query_text:
            return []

        topic = "news" if any(
            word in query_text.lower()
            for word in [
                "news",
                "today",
                "latest",
                "breaking",
                "செய்தி",
                "இன்று",
                "current",
            ]
        ) else "general"

        try:
            client = TavilyClient(api_key=self.api_key)
            results_limit = max_results or self.max_results
            payload: Dict[str, Any] = {
                "query": query_text,
                "topic": topic,
                "search_depth": "basic",
                "max_results": results_limit,
            }
            response = client.search(**payload)
        except TypeError:
            client = TavilyClient(api_key=self.api_key)
            response = client.search(
                query=query_text,
                topic=topic,
                search_depth="basic",
                num_results=max_results or self.max_results,
            )
        except Exception as exc:
            raise RuntimeError(f"Tavily search failed: {exc}") from exc

        raw_results: List[Dict[str, Any]] = []
        if isinstance(response, dict):
            raw_results = response.get("results") or []

        normalized: List[Dict[str, str]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url") or "").strip()
            if not url:
                continue

            title = str(item.get("title") or item.get("name") or "Untitled")
            snippet = (
                item.get("content")
                or item.get("snippet")
                or item.get("excerpt")
                or "No summary available."
            )
            date_value = (
                item.get("published_date")
                or item.get("date")
                or item.get("publishedAt")
                or "Date not available"
            )

            normalized.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": str(snippet),
                    "date": str(date_value),
                }
            )

        return normalized


class CodingAgent(GroqAgent):
    """Coding specialist."""

    def answer(self, question: str, history: Optional[List[Dict[str, str]]] = None):
        return self.generate(
            question,
            "You are an expert coding assistant. Explain Python, Streamlit, HTML, CSS, JavaScript, APIs, debugging, and product code clearly. Respond in English and simple Tamil when helpful. Provide concise but useful examples.",
            history,
        )


class StudyAgent(GroqAgent):
    """Study assistant."""

    def explain(self, topic: str, history: Optional[List[Dict[str, str]]] = None):
        return self.generate(
            topic,
            "You are a patient teacher. Explain concepts in simple Tamil and English with examples, analogies, and step-by-step guidance. Keep answers clear and beginner-friendly.",
            history,
        )


class MasterAgent:
    """Coordinator for all agent workflows."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        search_api_key: Optional[str] = None,
    ):
        self.groq_agent = GroqAgent(api_key=api_key, model=model)
        self.coding_agent = CodingAgent(api_key=api_key, model=model)
        self.study_agent = StudyAgent(api_key=api_key, model=model)
        self.search_agent = InternetSearchAgent(
            api_key=search_api_key or get_secret("TAVILY_API_KEY"),
            max_results=5,
        )

    def _generic_answer(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        answer = self.groq_agent.generate(
            prompt,
            "You are VENU AI, a helpful bilingual assistant for Tamil and English users. Answer clearly, respectfully, and accurately. Use simple language and a supportive tone.",
            history,
        )
        return {
            "answer": answer,
            "used_internet_search": False,
            "search_results": [],
        }

    def handle_internet_search(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        try:
            results = self.search_agent.search(prompt, max_results=5)
        except RuntimeError as exc:
            return {
                "answer": (
                    "Live internet search is unavailable because the Tavily API key is missing or invalid. "
                    "Add TAVILY_API_KEY to Streamlit Secrets to enable live web results."
                ),
                "used_internet_search": False,
                "search_results": [],
                "error": str(exc),
            }

        search_context = "\n".join(
            f"{index}. {item.get('title', 'Untitled')}\nURL: {item.get('url', '')}\nSummary: {item.get('snippet', '')}"
            for index, item in enumerate(results, start=1)
        )

        answer = self.groq_agent.generate(
            f"Use the following live search results to answer the user's question accurately and clearly.\n\nUser question: {prompt}\n\nSearch results:\n{search_context}",
            "You are a truthful research assistant. Answer using the provided search results, cite key findings, and say when information is uncertain. Respond in English and simple Tamil as needed.",
            history,
        )

        return {
            "answer": answer,
            "used_internet_search": True,
            "search_results": results,
        }

    def handle_coding(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        return {
            "answer": self.coding_agent.answer(prompt, history),
            "used_internet_search": False,
            "search_results": [],
        }

    def handle_study(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        return {
            "answer": self.study_agent.explain(prompt, history),
            "used_internet_search": False,
            "search_results": [],
        }

    def handle(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        lower_prompt = str(prompt).lower()

        if any(
            keyword in lower_prompt
            for keyword in [
                "latest",
                "news",
                "today",
                "breaking",
                "search the web",
                "internet",
                "current affairs",
                "recent",
                "update",
                "செய்தி",
                "இன்று",
                "தற்போது",
                "வலை",
            ]
        ):
            return self.handle_internet_search(prompt, history)

        if any(
            keyword in lower_prompt
            for keyword in [
                "code",
                "python",
                "streamlit",
                "javascript",
                "html",
                "css",
                "bug",
                "debug",
                "error",
                "fix",
                "api",
                "function",
                "class",
                "module",
                "script",
                "குறியீடு",
                "பிழை",
                "செயல்பாடு",
                "பிழைத்திருத்தம்",
            ]
        ):
            return self.handle_coding(prompt, history)

        if any(
            keyword in lower_prompt
            for keyword in [
                "study",
                "learn",
                "explain",
                "what is",
                "why",
                "how does",
                "biology",
                "math",
                "physics",
                "chemistry",
                "history",
                "lesson",
                "படிக்க",
                "கற்றுக்கொள்ள",
                "விளக்க",
                "பாடம்",
            ]
        ):
            return self.handle_study(prompt, history)

        return self._generic_answer(prompt, history)
