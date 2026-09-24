import argparse
import asyncio
import json
import random
import hashlib
import os
import sys
from typing import List, Dict, Any

from app.db.session import AsyncSessionFactory
from app.db.models.chunk import Chunk
from app.ai.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy import select

def get_text_fingerprint(text: str) -> str:
    """Stable chunk identification via SHA-256 fingerprint."""
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()

PROMPT = """You are an expert dataset creator for testing a RAG system.
Given the following context from one or more chunks of a document, generate a Question and a Grounded Answer based solely on the text.
The question should have distinct style depending on the instruction.

Respond strictly in valid JSON format:
{
    "question": "<your question>",
    "reference_answer": "<your answer>"
}
Do not use markdown blocks like ```json outside the JSON."""

async def generate_qa_pair(context_text: str, question_style: str = "factual") -> dict:
    llm = get_llm(streaming=False)
    
    style_guide = ""
    if question_style == "paraphrased":
        style_guide = "Use indirect, paraphrased phrasing. Don't use the exact keywords from the text."
    elif question_style == "multi-chunk":
        style_guide = "Create a question that strictly requires information from multiple distinct parts of the provided context."
    else:
        style_guide = "Create a direct factual lookup question."

    msgs = [
        SystemMessage(content=PROMPT),
        HumanMessage(content=f"Style Instruction: {style_guide}\n\nContext chunk(s):\n{context_text}")
    ]
    resp = await llm.ainvoke(msgs)
    content = resp.content.strip()
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        return json.loads(content)
    except Exception as e:
        # Fallback regex if LLM didn't respect JSON perfectly
        import re
        q = re.search(r'"question"\s*:\s*"([^"]+)"', content)
        a = re.search(r'"reference_answer"\s*:\s*"([^"]+)"', content)
        if q and a:
            return {"question": q.group(1), "reference_answer": a.group(1)}
        raise ValueError(f"Failed to parse LLM output: {content}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-questions", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="backend/evaluation/evaluation_dataset.json")
    parser.add_argument("--review", action="store_true", help="Launch interactive CLI review step")
    
    args = parser.parse_args()
    random.seed(args.seed)

    if args.review:
        await review_dataset(args.output)
        return

    # Check if dataset already exists
    dataset = []
    if os.path.exists(args.output):
        with open(args.output, "r", encoding="utf-8") as f:
            try:
                dataset = json.load(f)
            except json.JSONDecodeError:
                dataset = []
            
    existing_q_count = len([x for x in dataset if x["label_status"] in ["needs_review", "human_verified"]])
    
    if existing_q_count >= args.num_questions:
        print(f"Dataset already has {existing_q_count} questions. Use --review to review them.")
        return

    questions_needed = args.num_questions - existing_q_count
    print(f"Generating {questions_needed} new questions...")

    async with AsyncSessionFactory() as db:
        res = await db.execute(select(Chunk).order_by(Chunk.document_id, Chunk.chunk_index))
        all_chunks = res.scalars().all()

    if not all_chunks:
        print("Error: No chunks found in the database. Please upload a document first.")
        return

    # Let's group chunks by document for multi-chunk generation
    doc_to_chunks = {}
    for c in all_chunks:
        doc_to_chunks.setdefault(str(c.document_id), []).append(c)

    # 10% unanswerable, 20% multi-chunk, 40% paraphrased, 30% factual
    unanswerable_count = max(1, int(questions_needed * 0.10))
    multi_chunk_count = max(1, int(questions_needed * 0.20))
    paraphrased_count = max(1, int(questions_needed * 0.40))
    factual_count = questions_needed - unanswerable_count - multi_chunk_count - paraphrased_count
    
    unanswerables = [
        "What is the exact financial revenue reported for Q6 2050?",
        "How do I cook a perfect medium-rare steak?",
        "What are the specific planetary coordinates for Mars in 2500?",
        "Who won the 1994 World Cup according to the employee manuals?",
        "Detailed architectural differences between 12th and 13th century Gothic cathedrals?",
        "What is the average running speed of a cheetah in zero gravity?"
    ]
    
    new_entries = []
    offset = len(dataset) + 1

    # Generate Unanswerable
    for i, q in enumerate(random.choices(unanswerables, k=unanswerable_count)):
        new_entries.append({
            "id": f"q_{offset:03d}",
            "question": q,
            "document_id": None,
            "relevant_chunks": [],
            "reference_answer": "This information is not provided in the documents.",
            "label_status": "needs_review",
            "is_unanswerable": True,
            "type": "unanswerable"
        })
        offset += 1

    # Flatten all chunks for random factual / paraphrased sampling
    sampled_chunks = random.sample(all_chunks, min(factual_count + paraphrased_count, len(all_chunks)))
    
    tasks = []
    
    # 1. Generate Factual
    for chunk in sampled_chunks[:factual_count]:
        tasks.append(("factual", [chunk]))
        
    # 2. Generate Paraphrased
    for chunk in sampled_chunks[factual_count:factual_count+paraphrased_count]:
        tasks.append(("paraphrased", [chunk]))
        
    # 3. Generate Multi-Chunk
    # Select adjacent chunks within the same document if possible
    valid_docs = [k for k, v in doc_to_chunks.items() if len(v) >= 2]
    if not valid_docs:
        print("Warning: No documents have >= 2 chunks. Multi-chunk questions will fallback to single chunk.")
    
    for _ in range(multi_chunk_count):
        if valid_docs:
            did = random.choice(valid_docs)
            chunks_list = doc_to_chunks[did]
            start_idx = random.randint(0, len(chunks_list) - 2)
            c1, c2 = chunks_list[start_idx], chunks_list[start_idx+1]
            tasks.append(("multi-chunk", [c1, c2]))
        else:
            task_chunk = random.choice(all_chunks)
            tasks.append(("multi-chunk", [task_chunk]))

    # Execute all generations
    for style, chunk_objs in tasks:
        context_text = "\n\n---\n\n".join([c.content for c in chunk_objs])
        fingerprints = [get_text_fingerprint(c.content) for c in chunk_objs]
        doc_id_val = str(chunk_objs[0].document_id) if chunk_objs else None

        try:
            qa = await generate_qa_pair(context_text, style)
            entry = {
                "id": f"q_{offset:03d}",
                "question": qa["question"],
                "document_id": doc_id_val,
                "relevant_chunks": fingerprints,
                "reference_answer": qa["reference_answer"],
                "label_status": "needs_review",
                "is_unanswerable": False,
                "type": style
            }
            new_entries.append(entry)
            print(f"Generated ({style}): {qa['question']}")
            offset += 1
        except Exception as e:
            print(f"Failed to generate for chunk [{style}]: {e}", file=sys.stderr)

    dataset.extend(new_entries)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"\nAdded {len(new_entries)} questions to {args.output}")
    print("Run this script with --review to manually verify the dataset.")

async def review_dataset(filepath: str):
    if not os.path.exists(filepath):
        print("Dataset not found!")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    print("\n--- interactive review ---")
    modified = False
    for item in dataset:
        if item["label_status"] == "needs_review":
            print("\n" + "="*50)
            print(f"Type: {item.get('type')}")
            print(f"Question: {item['question']}")
            print(f"Ref Answer: {item['reference_answer']}")
            print(f"Unanswerable: {item.get('is_unanswerable', False)}")
            print(f"Relevant Chunks Count: {len(item.get('relevant_chunks', []))}")
            
            choice = input("Accept (a), Edit Answer (e), Reject(r), Skip(s), Quit(q)? [a/e/r/s/q]: ").strip().lower()
            if choice == 'a':
                item["label_status"] = "human_verified"
                modified = True
            elif choice == 'e':
                new_ans = input("New Reference Answer: ")
                item["reference_answer"] = new_ans
                item["label_status"] = "human_verified"
                modified = True
            elif choice == 'r':
                item["label_status"] = "rejected"
                modified = True
            elif choice == 'q':
                break
    
    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)
        print("Saved reviewed dataset.")
    else:
        print("No changes made.")

if __name__ == "__main__":
    asyncio.run(main())
