"""
Unit tests for Pydantic v2 schemas and LangChain prompt templates.
"""
import unittest
import uuid
from datetime import datetime
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.schemas.document import DocumentResponse
from app.schemas.chat import (
    CreateChatRequest,
    UpdateChatRequest,
    UserMessageRequest,
    MessageResponse,
    ChatResponse,
    ChatDetailResponse,
)
from app.ai.prompts import rag_prompt_template, rewrite_prompt_template


class TestSchemas(unittest.TestCase):
    def test_register_request_validation(self):
        # Valid
        req = RegisterRequest(email="test@example.com", password="password123")
        self.assertEqual(req.email, "test@example.com")

        # Invalid email
        with self.assertRaises(ValidationError):
            RegisterRequest(email="invalid-email", password="password123")

        # Password too short (< 8 chars)
        with self.assertRaises(ValidationError):
            RegisterRequest(email="test@example.com", password="short")

    def test_update_chat_request_validation(self):
        req = UpdateChatRequest(title="Updated Title")
        self.assertEqual(req.title, "Updated Title")

        # Empty title
        with self.assertRaises(ValidationError):
            UpdateChatRequest(title="")

    def test_chat_detail_response_serialization(self):
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        msg_id = uuid.uuid4()
        now = datetime.now()

        msg = MessageResponse(
            id=msg_id,
            role="assistant",
            content="Hello world",
            citations=[{"document_id": str(uuid.uuid4()), "filename": "doc.pdf"}],
            created_at=now,
        )

        detail = ChatDetailResponse(
            id=chat_id,
            user_id=user_id,
            title="My Chat",
            created_at=now,
            messages=[msg],
        )

        self.assertEqual(len(detail.messages), 1)
        self.assertEqual(detail.messages[0].role, "assistant")


class TestPrompts(unittest.TestCase):
    def test_rag_prompt_template_formatting(self):
        formatted = rag_prompt_template.format(context="[Doc test.pdf, Chunk 0]\nSome content")
        self.assertIn("Some content", formatted)
        self.assertIn("RULES:", formatted)

    def test_rewrite_prompt_template_formatting(self):
        formatted = rewrite_prompt_template.format(
            history="User: What is RAG?\nAssistant: RAG is Retrieval-Augmented Generation.",
            query="How does it work?",
        )
        self.assertIn("What is RAG?", formatted)
        self.assertIn("How does it work?", formatted)
        self.assertIn("STANDALONE SEARCH QUERY:", formatted)


if __name__ == "__main__":
    unittest.main()
