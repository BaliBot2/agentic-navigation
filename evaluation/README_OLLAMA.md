# Ollama-Based Evaluation

This directory contains scripts to evaluate the agent using **local Ollama models** instead of cloud APIs, avoiding rate limits.

## Files

- **`run_eval_ollama.py`**: Main orchestrator script (use this!)
- **`evaluate_with_ollama.py`**: Evaluation script using Ollama as judge
- **`generate_dataset.py`**: Generates questions from code_structure.json
- **`run_agent.py`**: Runs the agent against the dataset

## Quick Start

1. **Make sure Ollama is running:**
   ```bash
   ollama serve
   ```

2. **Run the evaluation:**
   ```bash
   python evaluation/run_eval_ollama.py
   ```

3. **Check the results:**
   ```bash
   cat evaluation/report_ollama.md
   ```

## Configuration

Edit `evaluate_with_ollama.py` to change the model:

```python
OLLAMA_MODEL = "llama3.2"  # Change to your preferred model
```

Available models on your system:
- Run `ollama list` to see installed models
- Popular options: `llama3.2`, `llama3.1`, `mistral`, `phi3`

## Metrics Provided

The Ollama-based evaluation provides:

### Overall Metrics
- **Accuracy**: Percentage of correct answers
- **Error Rate**: Percentage of errors (agent failures)
- **Correct/Incorrect/Error counts**

### By Question Type
- **Signature Questions Accuracy**: How well the agent identifies function signatures
- **File Lookup Questions Accuracy**: How well the agent identifies file locations

## Advantages Over API-Based Evaluation

✅ **No rate limits** - Run as many evaluations as you want  
✅ **No API costs** - Completely free  
✅ **Privacy** - All data stays local  
✅ **Faster** - No network latency  
✅ **Customizable** - Use any Ollama model you prefer

## Troubleshooting

**"Connection refused" error:**
- Make sure Ollama is running: `ollama serve`
- Check if Ollama is accessible: `curl http://localhost:11434`

**Model not found:**
- Install the model: `ollama pull llama3.2`
- Update `OLLAMA_MODEL` in `evaluate_with_ollama.py`

**Agent response extraction errors:**
- These are being worked on - the agent IS answering but we need to fix the text extraction
