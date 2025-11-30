"""
Fast Multi-Model Evaluation Script
Uses direct LLM calls instead of ReAct agent for speed
"""
import json
import os
import asyncio
from tqdm import tqdm
import time
import requests

DATASET_FILEPATH = "evaluation/dataset.json"
RESULTS_DIR = "evaluation/results"
REPORT_FILE = "evaluation/multi_model_report.md"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Models to evaluate
MODELS_TO_TEST = [
    "llama3.2",
    "phi3",
    "codellama"
]

def load_code_structure():
    """Load code structure for context"""
    with open("code_structure.json", "r") as f:
        return json.load(f)

def ask_ollama(model, prompt, timeout=60):
    """Ask Ollama a question directly"""
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            return f"Error: HTTP {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

def evaluate_model(model_name, dataset, code_structure):
    """Evaluate a single model on the dataset"""
    print(f"\n{'='*60}")
    print(f"Evaluating model: {model_name}")
    print(f"{'='*60}")
    
    results = []
    code_map = code_structure.get("code_map", {})
    
    # Create a simplified context string
    context = f"Code Map (showing function signatures and their files):\n"
    # Only include first 50 entries to keep context small
    for i, (key, value) in enumerate(list(code_map.items())[:50]):
        context += f"- '{key}' is defined in {value.get('file', 'unknown')}\n"
        if 'signature' in value:
            context += f"  Signature: {value['signature']}\n"
    
    for item in tqdm(dataset, desc=f"{model_name}"):
        question = item["question"]
        start_time = time.time()
        
        # Create prompt with context
        prompt = f"""{context}

Question: {question}

Please answer concisely based on the code map above. If asking for a signature, provide just the signature. If asking for a file, provide just the filename."""

        answer = ask_ollama(model_name, prompt, timeout=30)
        elapsed_time = time.time() - start_time
        
        results.append({
            "question": question,
            "ground_truth": item["ground_truth"],
            "agent_answer": answer,
            "type": item["type"],
            "model": model_name,
            "time_seconds": round(elapsed_time, 2)
        })
    
    return results

def judge_results(results, judge_model="llama3.2"):
    """Judge results using Ollama"""
    print(f"\nJudging results with {judge_model}...")
    
    for item in tqdm(results, desc="Judging"):
        if "Error:" in item["agent_answer"]:
            item["judgment"] = "ERROR"
            item["is_correct"] = False
            continue
        
        question = item["question"]
        ground_truth = item["ground_truth"]
        agent_answer = item["agent_answer"]
        
        prompt = f"""Question: {question}
Ground Truth: {ground_truth}
Agent Answer: {agent_answer}

Is the agent answer correct? Consider semantic equivalence.
Respond with ONLY "CORRECT" or "INCORRECT"."""

        judgment = ask_ollama(judge_model, prompt, timeout=20)
        
        # Clean up judgment
        if "CORRECT" in judgment.upper() and "INCORRECT" not in judgment.upper():
            item["judgment"] = "CORRECT"
            item["is_correct"] = True
        elif "INCORRECT" in judgment.upper():
            item["judgment"] = "INCORRECT"
            item["is_correct"] = False
        else:
            item["judgment"] = judgment
            item["is_correct"] = False
    
    return results

def generate_report(all_results):
    """Generate comparison report"""
    by_model = {}
    for result in all_results:
        model = result.get("model", "unknown")
        if model not in by_model:
            by_model[model] = []
        by_model[model].append(result)
    
    report = "# Multi-Model Evaluation Report\n\n"
    report += "## Model Comparison\n\n"
    report += "| Model | Accuracy | Precision | Recall | F1 Score | Error Rate | Avg Time (s) |\n"
    report += "|:------|:---------|:----------|:-------|:---------|:-----------|:-------------|\n"
    
    for model in MODELS_TO_TEST:
        if model not in by_model:
            continue
            
        results = by_model[model]
        total = len(results)
        
        # True Positives: Correct answers
        tp = sum(1 for r in results if r.get("is_correct", False))
        # False Positives: Incorrect answers (model answered but was wrong)
        fp = sum(1 for r in results if not r.get("is_correct", False) and "Error" not in r["agent_answer"])
        # False Negatives: Errors (model couldn't answer)
        fn = sum(1 for r in results if "Error" in r["agent_answer"])
        # True Negatives: Not applicable in this context
        
        errors = sum(1 for r in results if "Error" in r["agent_answer"])
        avg_time = sum(r.get("time_seconds", 0) for r in results) / total if total > 0 else 0
        
        # Calculate metrics
        accuracy = (tp / total * 100) if total > 0 else 0
        precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0
        recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
        error_rate = (errors / total * 100) if total > 0 else 0
        
        report += f"| {model} | {accuracy:.1f}% | {precision:.1f}% | {recall:.1f}% | {f1_score:.1f}% | {error_rate:.1f}% | {avg_time:.2f} |\n"
    
    report += "\n## Breakdown by Question Type\n\n"
    report += "| Model | Signature Acc | File Acc |\n"
    report += "|:------|:--------------|:---------|\n"
    
    for model in MODELS_TO_TEST:
        if model not in by_model:
            continue
            
        results = by_model[model]
        sig_results = [r for r in results if "signature" in r["question"].lower()]
        file_results = [r for r in results if "which file" in r["question"].lower()]
        
        sig_correct = sum(1 for r in sig_results if r.get("is_correct", False))
        file_correct = sum(1 for r in file_results if r.get("is_correct", False))
        
        sig_acc = (sig_correct / len(sig_results) * 100) if sig_results else 0
        file_acc = (file_correct / len(file_results) * 100) if file_results else 0
        
        report += f"| {model} | {sig_acc:.1f}% | {file_acc:.1f}% |\n"
    
    report += "\n## Detailed Results by Model\n\n"
    
    for model in MODELS_TO_TEST:
        if model not in by_model:
            continue
            
        report += f"### {model}\n\n"
        report += "| Question | Judgment | Answer | Ground Truth | Time |\n"
        report += "|:---------|:---------|:-------|:-------------|:-----|\n"
        
        for r in by_model[model]:
            q = r["question"].replace("|", "\\|")[:40]
            j = r.get("judgment", "N/A")
            a = r["agent_answer"].replace("|", "\\|").replace("\n", " ")[:60]
            gt = str(r["ground_truth"]).replace("|", "\\|")[:40]
            t = r.get("time_seconds", 0)
            report += f"| {q} | {j} | {a} | {gt} | {t:.2f}s |\n"
        
        report += "\n"
        
    return report

def main():
    # Load dataset
    if not os.path.exists(DATASET_FILEPATH):
        print(f"Error: {DATASET_FILEPATH} not found")
        return
    
    with open(DATASET_FILEPATH, "r") as f:
        dataset = json.load(f)
    
    print(f"Loaded {len(dataset)} questions")
    print(f"Models to test: {', '.join(MODELS_TO_TEST)}")
    
    # Load code structure
    code_structure = load_code_structure()
    
    # Create results directory
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Evaluate each model
    all_results = []
    for model in MODELS_TO_TEST:
        try:
            results = evaluate_model(model, dataset, code_structure)
            all_results.extend(results)
            
            # Save intermediate results
            with open(f"{RESULTS_DIR}/results_{model}.json", "w") as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"\nError evaluating {model}: {e}")
            continue
    
    # Judge results
    print("\n" + "="*60)
    all_results = judge_results(all_results)
    
    # Save all results
    with open(f"{RESULTS_DIR}/all_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    # Generate report
    report = generate_report(all_results)
    
    with open(REPORT_FILE, "w") as f:
        f.write(report)
    
    print("\n" + "="*60)
    print("✅ Multi-model evaluation complete!")
    print(f"Report saved to: {REPORT_FILE}")
    print(f"Results saved to: {RESULTS_DIR}/")
    print("="*60)

if __name__ == "__main__":
    main()
