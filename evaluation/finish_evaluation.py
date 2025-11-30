import json
import os
import sys
import requests
from tqdm import tqdm

RESULTS_DIR = "evaluation/results"
REPORT_FILE = "evaluation/multi_model_report.md"
JUDGE_MODEL = "llama3.2"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

def evaluate_with_ollama_judge(results):
    print(f"\nEvaluating {len(results)} results with judge model: {JUDGE_MODEL}")
    
    evaluated_results = []
    
    for item in tqdm(results, desc="Judging"):
        question = item["question"]
        ground_truth = item["ground_truth"]
        agent_answer = item["agent_answer"]
        
        # Skip if already judged (optional check)
        if "judgment" in item:
            evaluated_results.append(item)
            continue

        if "Error:" in agent_answer or "assistant: I couldn't find" in agent_answer or "assistant: Unfortunately" in agent_answer:
             # Heuristic: if agent says it couldn't find it, it's likely incorrect or at least not a direct answer.
             # But let's let the judge decide, or mark as INCORRECT if it's an explicit error.
             if "Error:" in agent_answer:
                item["judgment"] = "ERROR"
                item["is_correct"] = False
                evaluated_results.append(item)
                continue
        
        prompt = f"""You are an impartial judge. Is the Agent Answer correct based on the Ground Truth?

Question: {question}
Ground Truth: {ground_truth}
Agent Answer: {agent_answer}

Consider semantic equivalence. Respond with ONLY "CORRECT" or "INCORRECT"."""

        try:
            response = requests.post(
                OLLAMA_API_URL,
                json={"model": JUDGE_MODEL, "prompt": prompt, "stream": False},
                timeout=30
            )
            
            if response.status_code == 200:
                judgment = response.json()["response"].strip().upper()
                # Cleanup judgment string
                if "CORRECT" in judgment and "INCORRECT" not in judgment:
                    judgment = "CORRECT"
                elif "INCORRECT" in judgment:
                    judgment = "INCORRECT"
                
                item["judgment"] = judgment
                item["is_correct"] = "CORRECT" in judgment
            else:
                item["judgment"] = "ERROR"
                item["is_correct"] = False
                
        except Exception as e:
            item["judgment"] = f"ERROR: {str(e)}"
            item["is_correct"] = False
            
        evaluated_results.append(item)
    
    return evaluated_results

def generate_report(all_results):
    # Group by model
    by_model = {}
    for result in all_results:
        model = result.get("model", "unknown")
        if model not in by_model:
            by_model[model] = []
        by_model[model].append(result)
    
    report = "# Multi-Model Evaluation Report\n\n"
    report += "## Model Comparison\n\n"
    report += "| Model | Accuracy | Error Rate | Avg Time (s) | Signature Acc | File Acc |\n"
    report += "|:------|:---------|:-----------|:-------------|:--------------|:---------|\n"
    
    for model, results in by_model.items():
        total = len(results)
        correct = sum(1 for r in results if r.get("is_correct", False))
        errors = sum(1 for r in results if "Error" in r["agent_answer"] or r.get("judgment") == "ERROR")
        avg_time = sum(r.get("time_seconds", 0) for r in results) / total if total > 0 else 0
        
        sig_results = [r for r in results if "signature" in r["question"].lower()]
        file_results = [r for r in results if "which file" in r["question"].lower()]
        
        sig_correct = sum(1 for r in sig_results if r.get("is_correct", False))
        file_correct = sum(1 for r in file_results if r.get("is_correct", False))
        
        sig_acc = (sig_correct / len(sig_results) * 100) if sig_results else 0
        file_acc = (file_correct / len(file_results) * 100) if file_results else 0
        
        accuracy = (correct / total * 100) if total > 0 else 0
        error_rate = (errors / total * 100) if total > 0 else 0
        
        report += f"| {model} | {accuracy:.1f}% ({correct}/{total}) | {error_rate:.1f}% | {avg_time:.2f} | {sig_acc:.1f}% | {file_acc:.1f}% |\n"
    
    report += "\n## Detailed Results by Model\n\n"
    
    for model, results in by_model.items():
        report += f"### {model}\n\n"
        report += "| Question | Judgment | Answer | Time |\n"
        report += "|:---------|:---------|:-------|:-----|\n"
        
        for r in results:
            q = r["question"].replace("|", "\\|")[:50]
            j = r.get("judgment", "N/A")
            a = r["agent_answer"].replace("|", "\\|").replace("\n", " ")[:100]
            t = r.get("time_seconds", 0)
            report += f"| {q} | {j} | {a} | {t:.2f}s |\n"
        
        report += "\n"
        
    return report

def main():
    # Load llama3.2 results
    results_file = f"{RESULTS_DIR}/results_llama3.2.json"
    if not os.path.exists(results_file):
        print(f"Error: {results_file} not found")
        return

    with open(results_file, "r") as f:
        results = json.load(f)
    
    # Judge results
    judged_results = evaluate_with_ollama_judge(results)
    
    # Generate report
    report = generate_report(judged_results)
    
    with open(REPORT_FILE, "w") as f:
        f.write(report)
        
    print(f"Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    main()
