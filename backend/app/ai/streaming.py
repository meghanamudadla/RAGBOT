"""
Streaming SSE generator for the RAG chat pipeline.

WHY SSE OVER WEBSOCKET:
  SSE is unidirectional (server → client), which is exactly what we need
  for AI response streaming. It works over plain HTTP/1.1, needs no
  handshake upgrade, and is natively supported by EventSource in the
  browser. WebSockets add bidirectional overhead we don't need here.

HOW IT WORKS:
  1. User message is saved to DB.
  2. History is loaded and formatted for LangChain.
  3. Retriever fetches relevant chunks (vector search).
  4. LLM streams tokens via LangChain's astream() method.
  5. Each token chunk is sent as: `data: <token>\n\n`
  6. When done, the full response is saved to DB with citations.
  7. A final `data: [DONE]\n\n` event signals end-of-stream.
"""
import json
import uuid
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.ai.retriever import Retriever
from app.ai.llm import get_llm
from app.ai.prompts import rag_prompt_template, rewrite_prompt_template
from app.ai.groundedness import check_groundedness
from app.db.models.message import Message
from app.db.session import AsyncSessionFactory
from app.repositories.chat_repository import ChatRepository, MessageRepository


async def stream_rag_response(
    chat_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> AsyncGenerator[str, None]:
    """
    SSE generator for the RAG pipeline.

    IMPORTANT: This generator opens its own DB session instead of receiving
    one via Depends(get_db). FastAPI tears down yield-dependencies (closing
    the session) as soon as the endpoint returns — before the StreamingResponse
    body is actually consumed — so a request-scoped session would already be
    closed by the time the generator runs.
    """
    async with AsyncSessionFactory() as db:
        chat_repo = ChatRepository(db)
        msg_repo = MessageRepository(db)

        # 1. Validate chat ownership
        chat = await chat_repo.get(chat_id)
        if not chat or chat.user_id != user_id:
            yield f"data: {json.dumps({'error': 'Chat not found'})}\n\n"
            return

        # 2. Persist user message
        user_msg = Message(chat_id=chat_id, role="user", content=content)
        await msg_repo.create(user_msg)
        await db.commit()

        # 3. Load conversation history (limit to last 10 messages to preserve token window)
        db_msgs = await msg_repo.list_by_chat(chat_id)
        recent_db_msgs = db_msgs[:-1][-10:] if len(db_msgs) > 1 else []

        history = []
        for m in recent_db_msgs:
            if m.role == "user":
                history.append(HumanMessage(content=m.content))
            else:
                history.append(AIMessage(content=m.content))

        # 4. Contextual Query Rewriting
        search_query = content
        if len(recent_db_msgs) > 0:
            history_str = ""
            for m in recent_db_msgs:
                history_str += f"{m.role.capitalize()}: {m.content}\n"

            rewrite_llm = get_llm(streaming=False)
            rewrite_msg = rewrite_prompt_template.invoke({
                "history": history_str,
                "query": content
            })
            try:
                rewrite_resp = await rewrite_llm.ainvoke(rewrite_msg)
                search_query = rewrite_resp.content.strip()
            except Exception:
                pass  # fallback to original query if rewrite fails

        # 5. Retrieve context chunks using rewritten search query
        retriever = Retriever()
        hits = retriever.retrieve(search_query, str(user_id), top_k=5)

        context_parts = []
        for idx, hit in enumerate(hits, 1):
            context_parts.append(f"[{idx}]\n{hit['document']}")
        context_text = "\n\n".join(context_parts) if context_parts else "No relevant document excerpts were found for this user."

        system_prompt = rag_prompt_template.format(context=context_text)

        # 6. Stream LLM tokens
        llm = get_llm(streaming=True)
        messages_to_llm = [SystemMessage(content=system_prompt)] + history + [HumanMessage(content=content)]

        full_response = ""
        async for chunk in llm.astream(messages_to_llm):
            token = chunk.content
            if token:
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

        # 7. Build citations
        citations = [
            {
                "document_id": h["metadata"].get("document_id"),
                "filename": h["metadata"].get("filename"),
                "chunk_index": h["metadata"].get("chunk_index"),
                "distance": h.get("distance"),
            }
            for h in hits
        ]

        # 8. Check groundedness
        groundedness = check_groundedness(full_response, hits) if full_response and hits else {"overall_confidence": "low", "sentences": []}

        # 9. Persist AI message
        ai_msg = Message(
            chat_id=chat_id,
            role="assistant",
            content=full_response,
            citations=citations if citations else None,
            groundedness=groundedness,
        )
        await msg_repo.create(ai_msg)
        await db.commit()

        # 10. Send final event with citations so the client can render them
        yield f"data: {json.dumps({'done': True, 'citations': citations, 'groundedness': groundedness, 'message_id': str(ai_msg.id)})}\n\n"