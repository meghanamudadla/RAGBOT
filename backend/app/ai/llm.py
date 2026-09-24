"""
LLM Client using LangChain's Google GenAI integration.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def get_llm(streaming: bool = False) -> ChatGoogleGenerativeAI:
    """
    Returns an instance of Gemini model for LangChain.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=settings.GEMINI_API_KEY,
        streaming=streaming,
        temperature=0.1,  # Low temperature for fact-grounded RAG
    )
