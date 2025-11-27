# Installation Guide - Windows

## Quick Start (Without Ollama)

The project includes a **rule-based fallback** that allows you to test the system structure without installing Ollama. This is perfect for understanding how the agent works before committing to the full setup.

### Step 1: Install Python Dependencies

```powershell
# Make sure you're in the project directory
cd D:\Users\Nirasha\Documents\GitHub\Retail-analytics-Copilot

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Verify Setup

```powershell
python setup_check.py
```

You should see:
- ✓ Database loaded
- ✓ Views created  
- ✓ Document chunks loaded
- ⚠ DSPy using fallback (this is OK for testing)

### Step 3: Test Single Question

```powershell
python test_single.py
```

This will run a test query using the fallback LM.

### Step 4: Run Full Evaluation

```powershell
python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
```

Expected runtime: ~10-30 seconds (much faster than with Ollama)

### View Results

```powershell
# View results in PowerShell
Get-Content outputs_hybrid.jsonl | ConvertFrom-Json | Format-List

# Or open in notepad
notepad outputs_hybrid.jsonl
```

---

## Full Installation (With Ollama) - Optional

For production use with actual LLM inference, install Ollama:

### Step 1: Download Ollama

Visit [https://ollama.com/download/windows](https://ollama.com/download/windows) and download the installer.

### Step 2: Install Ollama

Run the installer and follow the prompts. This will:
- Install Ollama to `C:\Users\<YourName>\AppData\Local\Programs\Ollama`
- Add Ollama to your PATH
- Install Ollama as a Windows service

### Step 3: Verify Ollama Installation

Open a **new** PowerShell window (important - PATH needs to refresh):

```powershell
ollama --version
```

You should see something like: `ollama version is 0.x.x`

### Step 4: Pull the Model

```powershell
ollama pull phi3.5:3.8b-mini-instruct-q4_K_M
```

This downloads ~2.3GB and may take 5-10 minutes depending on your connection.

### Step 5: Verify Model

```powershell
ollama list
```

You should see `phi3.5:3.8b-mini-instruct-q4_K_M` in the list.

### Step 6: Start Ollama Service

Ollama usually starts automatically. If not:

```powershell
ollama serve
```

Keep this terminal open while running the agent.

### Step 7: Test with Real LLM

```powershell
# In a NEW PowerShell window
cd D:\Users\Nirasha\Documents\GitHub\Retail-analytics-Copilot
python test_single.py
```

You should now see "✓ Using Ollama with Phi-3.5-mini" instead of the fallback message.

---

## Troubleshooting

### "ollama is not recognized"

**Cause**: Ollama not installed or PATH not updated

**Solutions**:
1. Restart PowerShell after installing Ollama
2. Restart your computer (ensures PATH is refreshed)
3. Manually add to PATH:
   ```powershell
   $env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama\bin"
   ```
4. **Or just use the fallback** - it works for testing!

### "Import 'dspy' could not be resolved"

**Solution**:
```powershell
pip install dspy-ai --upgrade
```

### "Database not found"

**Solution**:
```powershell
# Re-download the database
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/dist/northwind.db" -OutFile "data/northwind.sqlite"
```

### Slow Performance with Ollama

**Expected**: First query takes 30-60 seconds (model loading)
**Subsequent**: 10-20 seconds per query

**Tips**:
- Use the Q4_K_M quantization (already specified)
- Close other applications
- Consider using the fallback for rapid testing
- Real deployment would use GPU acceleration

### Out of Memory (with Ollama)

**Requirements**: 
- Phi-3.5-mini needs ~4GB RAM for inference
- Total system: 8GB minimum, 16GB recommended

**Solution**: Use the fallback LM for testing on limited hardware

---

## Comparison: Fallback vs Ollama

| Feature | Fallback LM | Ollama + Phi-3.5 |
|---------|-------------|------------------|
| Installation | None needed | 5-10 minutes |
| Speed | Instant (<1s) | 10-20s per query |
| Memory | <100MB | ~4GB |
| Accuracy | Rule-based (good for known queries) | LLM-powered (adapts to new queries) |
| Internet | Not needed | Only for download |
| Best for | Testing, CI/CD, demos | Production, novel queries |

---

## What Works with Fallback?

✅ **Fully Functional**:
- Complete LangGraph workflow (all 8 nodes)
- Document retrieval (TF-IDF)
- SQL generation for common patterns
- SQL execution and repair loop
- Answer synthesis and formatting
- Citation tracking
- Confidence scoring

⚠ **Limited**:
- Novel query patterns not in fallback rules
- Complex natural language variations
- Nuanced reasoning

The fallback is **perfect for**:
- Understanding the architecture
- Testing your modifications
- Running CI/CD pipelines
- Demonstrations without setup overhead

---

## Recommended Workflow

1. **Start with Fallback** (5 minutes)
   - Test structure
   - Verify data loading
   - Understand flow

2. **Install Ollama if needed** (15 minutes)
   - Only if deploying to production
   - Or if testing novel queries
   - Or if you want full LLM capabilities

3. **Production Deployment**
   - Consider hosted LLM APIs (OpenAI, Anthropic)
   - Or dedicated GPU server with Ollama
   - Or edge deployment with fallback

---

## Next Steps

Choose your path:

### Path A: Quick Test (Recommended)
```powershell
pip install -r requirements.txt
python setup_check.py
python test_single.py
python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
```
Total time: **5 minutes**

### Path B: Full Setup
```powershell
# Install Ollama from https://ollama.com/download/windows
# Restart PowerShell
ollama pull phi3.5:3.8b-mini-instruct-q4_K_M
pip install -r requirements.txt
python setup_check.py
python test_single.py
python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
```
Total time: **20 minutes**

---

## Support

For issues:
1. Check this guide first
2. Run `setup_check.py` to diagnose
3. Review error messages carefully
4. Remember: **fallback mode works for testing!**
