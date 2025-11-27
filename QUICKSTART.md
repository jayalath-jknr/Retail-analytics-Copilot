# Quick Start Guide

## Installation (5 minutes)

### Step 1: Install Ollama
Download and install from [https://ollama.com](https://ollama.com)

### Step 2: Pull the Phi-3.5 Model
```bash
ollama pull phi3.5:3.8b-mini-instruct-q4_K_M
```

### Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Verify Setup
```bash
python setup_check.py
```

You should see all green checkmarks ✓

## Running the Agent

### Basic Usage
```bash
python run_agent_hybrid.py \
  --batch sample_questions_hybrid_eval.jsonl \
  --out outputs_hybrid.jsonl
```

### Expected Runtime
- 6 questions: ~2-3 minutes (depends on Ollama speed)
- Per question: ~20-30 seconds

### View Results
```bash
# Windows PowerShell
Get-Content outputs_hybrid.jsonl | ConvertFrom-Json | Format-List

# Or open in any text editor
notepad outputs_hybrid.jsonl
```

## Testing Individual Components

### Test Database Connection
```bash
python -m agent.tools.sqlite_tool
```

### Test Document Retrieval
```bash
python -m agent.rag.retrieval
```

### Test DSPy Modules
```bash
python -m agent.dspy_signatures
```

### Test Full Agent
```python
from agent.graph_hybrid import HybridAgent
import json

agent = HybridAgent()
result = agent.answer_question(
    question="What is the return policy for beverages?",
    format_hint="int",
    question_id="test1"
)
print(json.dumps(result, indent=2))
```

## Running DSPy Optimization

See how DSPy improves the NL2SQL module:

```bash
python optimize_example.py
```

This will show before/after metrics for SQL generation accuracy.

## Troubleshooting

### "Connection refused" error
- Ensure Ollama is running: `ollama serve`
- Check if model is downloaded: `ollama list`

### "Database not found"
- Database should be in `data/northwind.sqlite`
- Run setup_check.py to verify

### "No module named 'dspy'"
- Reinstall dependencies: `pip install -r requirements.txt`

### Slow performance
- First run is slower (model loading)
- Subsequent queries are faster
- Consider using a smaller model or CPU-optimized quantization

## Expected Output Format

Each question produces:
```json
{
  "id": "question_id",
  "final_answer": <typed_value>,
  "sql": "SELECT ... (if used)",
  "confidence": 0.85,
  "explanation": "Brief reasoning",
  "citations": ["table_name", "doc::chunk_id"]
}
```

## Sample Questions Explained

1. **rag_policy_beverages_return_days** → RAG-only, returns `14`
2. **hybrid_top_category_qty_summer_1997** → Needs docs for dates + SQL for data
3. **hybrid_aov_winter_1997** → KPI formula from docs + SQL calculation
4. **sql_top3_products_by_revenue_alltime** → Pure SQL aggregation
5. **hybrid_revenue_beverages_summer_1997** → Campaign dates + category filter
6. **hybrid_best_customer_margin_1997** → Cost approximation + margin calc

## Next Steps

1. Add your own questions to the JSONL file
2. Modify the document corpus in `docs/`
3. Explore the LangGraph visualization
4. Implement custom DSPy optimizers
5. Add more sophisticated confidence scoring

## Performance Tips

- **Batch processing**: Process multiple questions in one run
- **Cache results**: DSPy caches LM calls automatically
- **Optimize prompts**: Shorter prompts = faster responses
- **Parallel retrieval**: Already optimized in the code

## Support

For issues or questions:
- Check the README.md for detailed documentation
- Review the code comments in `agent/graph_hybrid.py`
- Inspect trace events in the agent state
