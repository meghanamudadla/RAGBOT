# RAG Evaluation Pipeline

This evaluation suite tests the retrieval and generation capabilities of the RAG platform. It strictly enforces isolation, bypassing PostgreSQL logging for evaluation runs, and computes deterministic metrics (Precision, Recall, MRR, Latency, and cross-encoder Groundedness) using text-fingerprinting for chunk identification.

## Prerequisites
Ensure your `.env` contains the required Gemini API Key and DB credentials. 
Your environment must be activated.

## Step 1: Building the Dataset
You need a ground-truth dataset before you can run metrics. Since the database chunk IDs are randomly generated UUIDs, the dataset relies on robust **SHA-256 text fingerprints** to track chunk recovery.

Run the automatic generator to read your uploaded chunks and draft QA pairs:
```powershell
python backend/evaluation/build_dataset.py --num-questions 50
```

## Step 2: Human Verification
The pipeline only scores questions marked as `"label_status": "human_verified"`. To review the drafted questions:
```powershell
python backend/evaluation/build_dataset.py --review
```
Use the interactive CLI to accept, edit, or reject the AI-generated reference answers.

## Step 3: Run Evaluation
Once your dataset contains verified questions, run the evaluation pipeline:
```powershell
python backend/evaluation/run_evaluation.py --dataset backend/evaluation/evaluation_dataset.json --num-questions 50 --k 5
```

## Outputs
After completion, check the `backend/evaluation/` directory for:
- `evaluation_results.json` (Full traces and summary)
- `EVALUATION_REPORT.md` (Human-readable markdown summary report)
- `evaluation_results.csv` (Spreadsheet view of per-query latency and scores)

## Testing the Math
To verify the isolated logic of the evaluation mathematics independent of LLMs:
```powershell
python backend/evaluation/metrics.py
```
