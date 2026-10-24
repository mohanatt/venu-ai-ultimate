from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from tavily import TavilyClient
from groq import Groq

SUPPORTED_GROQ_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
}

DEFAULT_GROQ_MODEL_ID = "llama-3.3-70b-versatile"


def resolve_model_id(model: Optional[str] = None) -> str:
    """Resolve the model ID and fall back to a currently supported Groq model."""
    candidate = (model or os.getenv("GROQ_MODEL_ID") or DEFAULT_GROQ_MODEL_ID).strip()
    if candidate in SUPPORTED_GROQ_MODELS:
        return candidate
    return DEFAULT_GROQ_MODEL_ID


class GroqAgent:
    """Base class for Groq-powered conversation agents."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = resolve_model_id(model)
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def _build_messages(
        self,
        user_prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if history:
            for entry in history:
                role = entry.get("role")
                content = entry.get("content")
                if role in {"user", "assistant"} and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_prompt})
        return messages

    def generate(
        self,
        user_prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not self.api_key or self.client is None:
            raise ValueError(
                "Groq API key is missing. Set GROQ_API_KEY in Streamlit secrets or environment variables."
            )

        messages = self._build_messages(user_prompt, system_prompt, history)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=800,
            )
        except Exception as exc:
            error_text = str(exc).lower()
            if "model_not_found" in error_text or "404" in error_text or "not found" in error_text:
                raise ValueError(
                    f"Groq model '{self.model}' is unavailable or not enabled for this account. "
                    "Set GROQ_MODEL_ID to a current supported Groq model, for example 'llama-3.3-70b-versatile'."
                ) from exc
            raise

        content = response.choices[0].message.content
        return (content or "").strip()


class InternetSearchAgent:
    """Search the web using Tavily."""

    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.api_key = os.getenv("TAVILY_API_KEY")

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, str]]:

        if not self.api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is missing. Add it in Streamlit Secrets."
            )

        try:
            client = TavilyClient(api_key=self.api_key)

            response = client.search(
                query=query,
                topic="news" if any(
                    word in query.lower()
                    for word in [
                        "news", "today", "latest",
                        "breaking", "செய்தி", "இன்று"
                    ]
                ) else "general",
                search_depth="basic",
                max_results=max_results or self.max_results,
            )

            results = []

            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "date": item.get("published_date", "Date not available"),
                })

            return results

        except Exception as exc:
            raise RuntimeError(
                f"Tavily search failed: {exc}"
            ) from exc

class CodingAgent(GroqAgent):
    """Coding specialist for code generation and troubleshooting."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key, model=resolve_model_id(model))

    def answer(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        system_prompt = (
            "You are an expert coding assistant. Explain Python, Streamlit, JavaScript, HTML, CSS, and debugging clearly. "
            "Give practical and production-safe answers. Keep responses concise but useful."
        )
        return self.generate(question, system_prompt=system_prompt, history=history)


class StudyAgent(GroqAgent):
    """Study specialist for learning and explanation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key, model=resolve_model_id(model))

    def explain(self, topic: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        system_prompt = (
            "You are a patient tutor. Explain concepts clearly in simple Tamil when helpful. "
            "Use examples and step-by-step explanations. Keep the answer easy to understand."
        )
        return self.generate(topic, system_prompt=system_prompt, history=history)


class MasterAgent:
    """Main orchestrator for all agents."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        selected_model = resolve_model_id(model)
        self.groq_agent = GroqAgent(api_key=self.api_key, model=selected_model)
        self.search_agent = InternetSearchAgent(max_results=5)
        self.coding_agent = CodingAgent(api_key=self.api_key, model=selected_model)
        self.study_agent = StudyAgent(api_key=self.api_key, model=selected_model)

    @staticmethod
    def _is_news_or_current_request(user_input: str) -> bool:
        lower = user_input.lower()
        news_signals = [
            "news",
            "latest",
            "today",
            "today's",
            "current news",
            "recent",
            "breaking",
            "current events",
            "world news",
            "what is happening",
            "latest information",
            "happening today",
            "what happened",
        ]
        return any(signal in lower for signal in news_signals)

    @staticmethod
    def _is_coding_request(user_input: str) -> bool:
        lower = user_input.lower()
        coding_signals = [
            "code",
            "python",
            "streamlit",
            "bug",
            "error",
            "debug",
            "fix",
            "function",
            "class",
            "script",
            "api",
        ]
        return any(signal in lower for signal in coding_signals)

    @staticmethod
    def _is_study_request(user_input: str) -> bool:
        lower = user_input.lower()
        study_signals = [
            "explain",
            "study",
            "learn",
            "what is",
            "how does",
            "why",
            "concept",
            "tutorial",
            "teach",
            "understand",
        ]
        return any(signal in lower for signal in study_signals)

    @staticmethod
    def _format_search_results(results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No internet results were found for this query."

        lines: List[str] = []
        for index, result in enumerate(results, start=1):
            title = result.get("title") or "Untitled"
            url = result.get("url") or ""
            snippet = result.get("snippet") or "No summary available."
            date_value = result.get("date") or "Date not available"
            lines.append(
                f"{index}. {title}\n"
                f"URL: {url}\n"
                f"Date: {date_value}\n"
                f"Summary: {snippet}\n"
            )
        return "\n".join(lines)

    def handle_internet_search(self, query: str) -> Dict[str, Any]:
        try:
            results = self.search_agent.search(query, max_results=5)
        except Exception as exc:
            return {
                "answer": (
                    "I could not fetch live internet search results right now. "
                    "Please check your internet connection and try again. "
                    f"Error: {exc}"
                ),
                "search_results": [],
                "used_internet_search": False,
            }

        if not results:
            return {
                "answer": "I searched the internet, but no current results were found for that query. Please try another question.",
                "search_results": [],
                "used_internet_search": True,
            }

        formatted_results = self._format_search_results(results)
        question = (
            "Answer the user's question using the search results below. Do not guess or invent facts. "
            "If the information is missing, say that clearly. When helpful, answer in Tamil.\n\n"
            f"User question: {query}\n\nSearch results:\n{formatted_results}"
        )

        answer = self.groq_agent.generate(
            user_prompt=question,
            system_prompt=(
                "You are a reliable assistant. Use the provided internet search results as the source of truth. "
                "Do not make up news, articles, or links. If there is not enough information, clearly say so."
            ),
        )

        return {
            "answer": answer,
            "search_results": results,
            "used_internet_search": True,
        }

    def handle_coding(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        answer = self.coding_agent.answer(question, history=history)
        return {
            "answer": answer,
            "search_results": [],
            "used_internet_search": False,
        }

    def handle_study(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        answer = self.study_agent.explain(question, history=history)
        return {
            "answer": answer,
            "search_results": [],
            "used_internet_search": False,
        }

    def handle(self, user_input: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not user_input or not user_input.strip():
            return {
                "answer": "Please enter a question or request.",
                "search_results": [],
                "used_internet_search": False,
            }

        if self._is_news_or_current_request(user_input):
            return self.handle_internet_search(user_input)

        if self._is_coding_request(user_input):
            return self.handle_coding(user_input, history=history)

        if self._is_study_request(user_input):
            return self.handle_study(user_input, history=history)

        answer = self.groq_agent.generate(
            user_prompt=user_input,
            system_prompt=(
                "Answer the user's question clearly and helpfully. Use Tamil when appropriate and keep the answer practical."
            ),
            history=history,
        )
        return {
            "answer": answer,
            "search_results": [],
            "used_internet_search": False,
        }


def get_agent_prompt(agent: str) -> str:
    prompts = {
        "Master Agent": (
            "You are VENU AI, a helpful AI assistant. Reply in simple Tamil when appropriate."
        ),
        "Coding Agent": (
            "You are an expert coding assistant. Explain Python, HTML, CSS, and JavaScript step by step."
        ),
        "Study Agent": (
            "You are a friendly tutor. Explain school subjects in simple Tamil with examples."
        ),
        "Internet Search Agent": (
            "You are an internet research assistant. Use current search results as the source of truth and never invent links or facts."
        ),
    }
    return prompts.get(agent, prompts["Master Agent"])
