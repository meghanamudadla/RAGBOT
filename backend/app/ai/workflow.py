"""
LangGraph workflow for the RAG pipeline.
"""
from typing import TypedDict, Sequence, Optional, Annotated
import operator

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.ai.retriever import Retriever
from app.ai.prompts import rag_prompt_template
from app.ai.llm import get_llm
from app.ai.groundedness import check_groundedness


class LLMState(TypedDict):
    """
    State representing the context being passed through the Graph.
    `messages` append via operator.add
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_id: str
    query: str
    context_chunks: Optional[list[dict]]
    system_prompt: Optional[str]
    response: Optional[str]
    groundedness: Optional[dict]


def retrieve_node(state: LLMState) -> LLMState:
    """Retrieve relevant document chunks based on the query."""
    query = state["query"]
    user_id = state["user_id"]
    
    retriever = Retriever()
    # retrieve top 5 semantic matches
    hits = retriever.retrieve(query, user_id, top_k=5)
    
    return {"context_chunks": hits}


def build_prompt_node(state: LLMState) -> LLMState:
    """Compile the retrieved chunks into a system prompt."""
    hits = state.get("context_chunks", [])
    
    if hits:
        context_parts = []
        for idx, hit in enumerate(hits, 1):
            context_parts.append(f"[{idx}]\n{hit['document']}")
        context_text = "\n\n".join(context_parts)
    else:
        context_text = "No relevant document excerpts were found for this user."
        
    system_prompt_str = rag_prompt_template.format(context=context_text)
    
    return {"system_prompt": system_prompt_str}


def generate_node(state: LLMState) -> LLMState:
    """Invoke the Gemini model with the system prompt and conversation history."""
    # We enable streaming inside the LLM definition
    llm = get_llm(streaming=True)
    
    # Construct final message list: SystemPrompt + History 
    messages_to_llm = []
    if state.get("system_prompt"):
        messages_to_llm.append(SystemMessage(content=state["system_prompt"]))
        
    # Append the historical conversation + current query
    messages_to_llm.extend(state.get("messages", []))
    
    response_msg = llm.invoke(messages_to_llm)
    
    return {"response": response_msg.content}


def verify_node(state: LLMState) -> LLMState:
    """Check groundedness of the generated response against retrieved chunks."""
    response = state.get("response", "")
    hits = state.get("context_chunks", [])
    
    if response and hits:
        groundedness = check_groundedness(response, hits)
    else:
        groundedness = {"overall_confidence": "low", "sentences": []}
    
    return {"groundedness": groundedness}


def build_workflow():
    """
    Compile the StateGraph for RAG interactions.
    Nodes: 
      - retrieve semantic context
      - build prompt with context + chat history
      - generate response using Gemini LLM
      - verify groundedness of response
    """
    workflow = StateGraph(LLMState)
    
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("build_prompt", build_prompt_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("verify", verify_node)
    
    # Edges: retrieve -> build_prompt -> generate -> verify -> END
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "build_prompt")
    workflow.add_edge("build_prompt", "generate")
    workflow.add_edge("generate", "verify")
    workflow.add_edge("verify", END)
    
    return workflow.compile()