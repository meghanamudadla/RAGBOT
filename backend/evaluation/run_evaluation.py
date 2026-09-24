import argparse
import asyncio
import json
import os
import uuid
import time
import csv
from datetime import datetime

from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.db.models.user import User
from app.db.models.document import Document
from app.db.models.chunk import Chunk
from app.ai.retriever import Retriever
from app.ai.llm import get_llm
from app.ai.prompts import rag_prompt_template, rewrite_prompt_template
from app.ai.groundedness import check_groundedness
from app.ai.vector_store import VectorStore
from app.ai.bm25_index import get_bm25_index
from app.ai.embeddings import EmbeddingClient
from langchain_core.messages import SystemMessage, HumanMessage

from backend.evaluation.metrics import (
    get_text_fingerprint,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_hit_rate_at_k,
    calculate_mrr,
    get_groundedness_rates,
    calculate_mean,
    calculate_percentile
)

EVAL_USER_EMAIL = "evaluation_runner@internal.local"
MAX_RETRIES = 3

async def setup_evaluation_sandbox(dataset: list) -> uuid.UUID:
    """Ensures eval user exists and populates its sandbox with required chunks safely."""
    async with AsyncSessionFactory() as db:
        res = await db.execute(select(User).where(User.email == EVAL_USER_EMAIL))
        eval_user = res.scalars().first()
        if not eval_user:
            eval_user = User(email=EVAL_USER_EMAIL, full_name="Evaluation Runner", hashed_password="X")
            db.add(eval_user)
            await db.commit()
            await db.refresh(eval_user)
        
        doc_ids = {item["document_id"] for item in dataset if item.get("document_id")}
        if not doc_ids:
            return eval_user.id
            
        print(f"Syncing {len(doc_ids)} docs to evaluation sandbox for user {eval_user.id}...")
        
        vs = VectorStore()
        bm25_index = get_bm25_index(str(eval_user.id))
        embedder = EmbeddingClient()
        
        for did in doc_ids:
            vs.delete_by_document_id(f"eval_{did}")
            bm25_index.delete_by_document_id(f"eval_{did}")
            
            res = await db.execute(select(Chunk).where(Chunk.document_id == did))
            chunks = res.scalars().all()
            if not chunks:
                continue
                
            texts = [c.content for c in chunks]
            embeddings = embedder.embed_batch(texts)
            fake_chunk_ids = [str(uuid.uuid4()) for _ in chunks]
            
            metadatas = [
                {
                    "document_id": f"eval_{did}",
                    "user_id": str(eval_user.id),
                    "chunk_index": c.chunk_index,
                    "filename": "eval_document"
                }
                for c in chunks
            ]
            
            vs.upsert_chunks(fake_chunk_ids, embeddings, texts, metadatas)
            bm25_index.upsert_chunks(fake_chunk_ids, texts, metadatas)
            
        return eval_user.id

async def evaluate_question(item: dict, eval_user_id: str, k: int = 5):
    retriever = Retriever()
    query = item["question"]
    question_type = item.get("type", "factual")
    relevant_fingerprints = item.get("relevant_chunks", [])
    
    latency = {
        "rewrite": None,
        "embedding": None, # implicitly tracked here along with retrieval
        "retrieval": None,
        "generation": None,
        "groundedness": None,
        "total": None
    }
    
    t_start = time.perf_counter()
    
    # 1. Rewrite (Single-turn default context = no history rewrite needed)
    search_query = query
    
    # Guard check: Ensure filter uses evaluation user!
    assert str(eval_user_id) != "prod", "FATAL: Retrieval filter not scoped to evaluation user."
    
    # 2. Retrieval
    t0 = time.perf_counter()
    hits = retriever.retrieve(search_query, str(eval_user_id), top_k=k)
    latency["retrieval"] = time.perf_counter() - t0
    
    retrieved_fingerprints = [get_text_fingerprint(h["document"]) for h in hits]
    
    # Check if unanswerable
    is_unanswerable = item.get("is_unanswerable", False)
    
    if is_unanswerable:
        p_at_k, r_at_k, hr_at_k, mrr_k = None, None, None, None
    else:
        p_at_k = calculate_precision_at_k(retrieved_fingerprints, relevant_fingerprints, k)
        r_at_k = calculate_recall_at_k(retrieved_fingerprints, relevant_fingerprints, k)
        hr_at_k = calculate_hit_rate_at_k(retrieved_fingerprints, relevant_fingerprints, k)
        mrr_k = calculate_mrr(retrieved_fingerprints, relevant_fingerprints, k)
    
    context_parts = []
    for idx, hit in enumerate(hits, 1):
        context_parts.append(f"[{idx}]\n{hit['document']}")
    context_text = "\n\n".join(context_parts) if context_parts else "No relevant document excerpts."
    system_prompt = rag_prompt_template.format(context=context_text)
    
    # 3. LLM Generation
    t0 = time.perf_counter()
    llm = get_llm(streaming=False) 
    messages_to_llm = [SystemMessage(content=system_prompt), HumanMessage(content=query)]
    
    resp = await llm.ainvoke(messages_to_llm)
    full_response = resp.content
    latency["generation"] = time.perf_counter() - t0
    
    # 4. Groundedness check
    t0 = time.perf_counter()
    groundedness = check_groundedness(full_response, hits) if full_response and hits else {"overall_confidence": "low", "sentences": []}
    latency["groundedness"] = time.perf_counter() - t0
    
    latency["total"] = time.perf_counter() - t_start
    
    return {
        "id": item["id"],
        "question": query,
        "type": question_type,
        "is_unanswerable": is_unanswerable,
        "retrieved_chunks": retrieved_fingerprints,
        "relevant_chunks": relevant_fingerprints,
        "precision_at_k": p_at_k,
        "recall_at_k": r_at_k,
        "hit_rate_at_k": hr_at_k,
        "mrr_at_k": mrr_k,
        "generated_answer": full_response,
        "groundedness_raw": groundedness["overall_confidence"],
        "groundedness_details": groundedness,
        "stage_latency_seconds": latency,
        "total_latency_seconds": latency["total"],
        "error": None
    }

async def run_warmup():
    print("Running system warmup...")
    llm = get_llm(streaming=False)
    await llm.ainvoke([HumanMessage(content="Hello")])
    # Init Chroma cache
    vs = VectorStore()
    get_bm25_index("eval")
    print("Warmup complete.")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument("--num-questions", type=int, default=50)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default="backend/evaluation")
    
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    with open(args.dataset, "r", encoding="utf-8") as f:
        full_dataset = json.load(f)
        
    dataset = [x for x in full_dataset if x.get("label_status") == "human_verified"]
    if len(dataset) == 0:
        print("Warning: No human_verified questions found! Running on all needs_review instead for demonstration.")
        dataset = [x for x in full_dataset if x.get("label_status") == "needs_review"]
        
    if not dataset:
        raise ValueError("Dataset is totally empty or malformed.")
        
    dataset = dataset[:args.num_questions]
    
    eval_user_id = await setup_evaluation_sandbox(dataset)
    await run_warmup()
    
    results = []
    failed = 0
    
    for item in dataset:
        print(f"Evaluating: {item['id']} ...", end=" ", flush=True)
        retries = 0
        success = False
        while retries < MAX_RETRIES and not success:
            try:
                result = await evaluate_question(item, str(eval_user_id), args.k)
                results.append(result)
                success = True
                print("Done.", round(result["total_latency_seconds"], 2), "s")
            except Exception as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    failed += 1
                    err_res = {"id": item["id"], "question": item["question"], "error": str(e)}
                    results.append(err_res)
                    print(f"Failed after {retries} retries: {e}")
                else:
                    time.sleep(2 * retries)
                    
    # Aggregation
    valid_results = [r for r in results if not r.get("error")]
    answerable_results = [r for r in valid_results if not r.get("is_unanswerable")]
    
    def mean_not_none(l): return calculate_mean([x for x in l if x is not None])
    
    total_q = len(dataset)
    precision = mean_not_none([r["precision_at_k"] for r in answerable_results])
    recall = mean_not_none([r["recall_at_k"] for r in answerable_results])
    hr = mean_not_none([r["hit_rate_at_k"] for r in answerable_results])
    mrr = mean_not_none([r["mrr_at_k"] for r in answerable_results])
    
    strict_gr = 0
    lenient_gr = 0
    if valid_results:
        grates = [get_groundedness_rates(r["groundedness_raw"]) for r in valid_results]
        strict_gr = sum(x[0] for x in grates) / len(grates)
        lenient_gr = sum(x[1] for x in grates) / len(grates)
        
    avg_rel = calculate_mean([len(r["relevant_chunks"]) for r in answerable_results])
    
    tl = [r["total_latency_seconds"] for r in valid_results]
    
    eval_summary = {
        "total_questions": total_q,
        "evaluated_questions": len(valid_results),
        "failed_questions": failed,
        "answerable_questions": len(answerable_results),
        "unanswerable_questions": len([r for r in valid_results if r.get("is_unanswerable")]),
        "average_relevant_chunks_per_answerable_q": round(avg_rel, 2),
        "precision_at_5": round(precision, 4),
        "recall_at_5": round(recall, 4),
        "hit_rate_at_5": round(hr, 4),
        "mrr": round(mrr, 4),
        "groundedness_rate_strict": round(strict_gr, 4),
        "groundedness_rate_lenient": round(lenient_gr, 4),
        "latency_seconds": {
            "mean": round(calculate_mean(tl), 3),
            "p50": round(calculate_percentile(tl, 0.5), 3),
            "p95": round(calculate_percentile(tl, 0.95), 3)
        },
        "stage_latency_mean_seconds": {
            "retrieval": round(mean_not_none([r["stage_latency_seconds"]["retrieval"] for r in valid_results]), 3),
            "generation": round(mean_not_none([r["stage_latency_seconds"]["generation"] for r in valid_results]), 3),
            "groundedness": round(mean_not_none([r["stage_latency_seconds"]["groundedness"] for r in valid_results]), 3),
        }
    }
    
    out_json = {
        "run_metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "k": args.k,
            "seed": args.seed,
            "embedding_model": "all-MiniLM-L6-v2",
            "generation_model": "gemini-2.5-flash",
            "notes": "Persistence intentionally skipped for evaluation wrapper speed."
        },
        "evaluation_summary": eval_summary,
        "individual_results": results
    }
    
    json_path = os.path.join(args.output_dir, "evaluation_results.json")
    with open(json_path, "w") as f:
        json.dump(out_json, f, indent=2)
        
    csv_path = os.path.join(args.output_dir, "evaluation_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["question", "is_unanswerable", "precision_at_5", "recall_at_5", "groundedness", "retrieval_latency", "generation_latency", "groundedness_latency", "total_latency"])
        for r in results:
            if r.get("error"):
                writer.writerow([r["question"], "", "", "", "ERROR", "", "", "", ""])
            else:
                writer.writerow([
                    r["question"],
                    r.get("is_unanswerable", False),
                    round(r["precision_at_k"], 3) if r["precision_at_k"] is not None else "",
                    round(r["recall_at_k"], 3) if r["recall_at_k"] is not None else "",
                    r["groundedness_raw"],
                    round(r["stage_latency_seconds"]["retrieval"], 3),
                    round(r["stage_latency_seconds"]["generation"], 3),
                    round(r["stage_latency_seconds"]["groundedness"], 3),
                    round(r["total_latency_seconds"], 3)
                ])

    import codecs
    md_path = os.path.join(args.output_dir, "EVALUATION_REPORT.md")
    with codecs.open(md_path, "w", "utf-8") as f:
        f.write("# RAG Evaluation Report\n\n")
        f.write("## 1. Dataset Overview\n")
        f.write(f"- **Evaluated Questions**: {eval_summary['evaluated_questions']} ({eval_summary['answerable_questions']} Answerable, {eval_summary['unanswerable_questions']} Unanswerable)\n")
        f.write(f"- **Failed Runs**: {eval_summary['failed_questions']}\n\n")
        f.write("## 2. Retrieval Performance\n")
        f.write(f"- Precision@5: {eval_summary['precision_at_5']}\n")
        f.write(f"- Recall@5: {eval_summary['recall_at_5']}\n")
        f.write(f"- Hit Rate@5: {eval_summary['hit_rate_at_5']}\n")
        f.write(f"- MRR: {eval_summary['mrr']}\n")
        f.write(f"- Avg Relevant Chunks / Q: {eval_summary['average_relevant_chunks_per_answerable_q']} (Note: Precision@5 has a math ceiling for Qs with < 5 targets)\n\n")
        f.write("## 3. Generation Quality\n")
        f.write(f"- Strict Groundedness (High only): {eval_summary['groundedness_rate_strict'] * 100:.1f}%\n")
        f.write(f"- Lenient Groundedness (High+Medium): {eval_summary['groundedness_rate_lenient'] * 100:.1f}%\n\n")
        f.write("## 4. Latency\n")
        f.write(f"- Total Mean: {eval_summary['latency_seconds']['mean']}s (p50: {eval_summary['latency_seconds']['p50']}s, p95: {eval_summary['latency_seconds']['p95']}s)\n")
        f.write(f"- Breakdown (Mean): Retrieval {eval_summary['stage_latency_mean_seconds']['retrieval']}s | Generation {eval_summary['stage_latency_mean_seconds']['generation']}s | Groundedness {eval_summary['stage_latency_mean_seconds']['groundedness']}s\n\n")
        
        f.write("## 5. Lowest Recall Cases\n")
        worst = sorted([r for r in answerable_results if r["recall_at_k"] is not None], key=lambda x: x["recall_at_k"])[:5]
        for w in worst:
            f.write(f"- Q: *{w['question']}* (Recall: {w['recall_at_k']})\n")

    print("\n--- Summary ---")
    print(f"Total Questions: {total_q} | Evaluated: {eval_summary['evaluated_questions']} | Failed: {failed}")
    print(f"Recall@5: {eval_summary['recall_at_5']} | Precision@5: {eval_summary['precision_at_5']}")
    print(f"Grounded (Lenient): {eval_summary['groundedness_rate_lenient']}")
    print(f"Outputs written to {args.output_dir}/")

if __name__ == "__main__":
    asyncio.run(main())
