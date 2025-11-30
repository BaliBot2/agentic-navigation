"""
Multi-Model Evaluation Script
Compares agent performance across different Ollama models
"""
import json
import os
import sys
import asyncio
from tqdm import tqdm
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATASET_FILEPATH = "evaluation/dataset.json"
RESULTS_DIR = "evaluation/results"

# Models to evaluate
MODELS_TO_TEST = [
    "llama3.2",
    "phi3",
    "codellama"
]

async def run_agent_with_model(model_name, dataset):
    """Run agent evaluation with a specific model"""
    from llama_index.llms.ollama import Ollama
    from llama_index.core import Settings
    from llama_index.core.tools import FunctionTool
    from llama_index.core.agent import ReActAgent
    
    # Load code map
    with open("code_structure.json", "r") as f:
        code_map_data = json.load(f)
    
    # Setup LLM
    Settings.llm = Ollama(model=model_name, request_timeout=120.0)
    
    # Define tools
    def get_code_map_info(query: str) -> str:
        if query in code_map_data:
            return json.dumps(code_map_data[query], indent=2)
        return "Invalid query. Available keys are 'code_map', 'file_dependencies', 'call_map'."
    
    def read_source_file(filename: str) -> str:
        filepath = os.path.normpath(os.path.join("./libpng", filename))
        if not filepath.startswith(os.path.normpath("./libpng")):
            return "Error: Access denied."
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File '{filename}' not found."
    
    tool_get_map_info = FunctionTool.from_defaults(fn=get_code_map_info)
    tool_read_file = FunctionTool.from_defaults(fn=read_source_file)
    
    # Create agent
    agent = ReActAgent(
        tools=[tool_get_map_info, tool_read_file],
        llm=Settings.llm,
        verbose=False,  # Reduce noise
    )
    
    results = []
    print(f"\n{'='*60}")
    print(f"Evaluating model: {model_name}")
    print(f"{'='*60}")
    
    for item in tqdm(dataset, desc=f"{model_name}"):
        question = item["question"]
        start_time = time.time()
        
        try:
            handler = agent.run(question)
            response = await handler
            
            # Extract answer
            answer = None
            if hasattr(response, 'response') and response.response:
                answer = str(response.response)
            elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                answer = str(response.message.content)
            else:
                answer = str(response)
                
            elapsed_time = time.time() - start_time
            
        except Exception as e:
            answer = f"Error: {str(e)}"
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

async def evaluate_with_ollama_judge(results, judge_model="llama3.2"):
    """Evaluate results using Ollama as judge"""
    import requests
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    print(f"\nEvaluating results with judge model: {judge_model}")
    
    for item in tqdm(results, desc="Judging"):
        question = item["question"]
        ground_truth = item["ground_truth"]
        agent_answer = item["agent_answer"]
        
        if "Error:" in agent_answer:
            item["judgment"] = "ERROR"
            item["is_correct"] = False
            continue
        
        prompt = f"""You are an impartial judge. Is the Agent Answer correct based on the Ground Truth?

Question: {question}
Ground Truth: {ground_truth}
Agent Answer: {agent_answer}

Consider semantic equivalence. Respond with ONLY "CORRECT" or "INCORRECT"."""

        try:
            response = requests.post(
                OLLAMA_API_URL,
                json={"model": judge_model, "prompt": prompt, "stream": False},
                timeout=30
            )
            
            if response.status_code == 200:
                judgment = response.json()["response"].strip().upper()
                item["judgment"] = judgment
                item["is_correct"] = "CORRECT" in judgment
            else:
                item["judgment"] = "ERROR"
                item["is_correct"] = False
                
        except Exception as e:
            item["judgment"] = f"ERROR: {str(e)}"
            item["is_correct"] = False
    
    return results

def generate_comparison_report(all_results):
    """Generate comparison report across models"""
    
    # Group by model
    by_model = {}
    for result in all_results:
        model = result["model"]
        if model not in by_model:
            by_model[model] = []
        by_model[model].append(result)
    
    # Calculate metrics per model
    model_metrics = {}
    for model, results in by_model.items():
        total = len(results)
        correct = sum(1 for r in results if r.get("is_correct", False))
        errors = sum(1 for r in results if "Error" in r["agent_answer"])
        avg_time = sum(r.get("time_seconds", 0) for r in results) / total if total > 0 else 0
        
        # By question type
        sig_results = [r for r in results if "signature" in r["question"].lower()]
        file_results = [r for r in results if "which file" in r["question"].lower()]
        
        sig_correct = sum(1 for r in sig_results if r.get("is_correct", False))
        file_correct = sum(1 for r in file_results if r.get("is_correct", False))
        
        model_metrics[model] = {
            "total": total,
            "correct": correct,
            "errors": errors,
            "accuracy": (correct / total * 100) if total > 0 else 0,
            "error_rate": (errors / total * 100) if total > 0 else 0,
            "avg_time": round(avg_time, 2),
            "signature_accuracy": (sig_correct / len(sig_results) * 100) if sig_results else 0,
            "file_accuracy": (file_correct / len(file_results) * 100) if file_results else 0,
        }
    
    # Generate report
    report = "# Multi-Model Evaluation Report\n\n"
    report += "## Model Comparison\n\n"
    report += "| Model | Accuracy | Error Rate | Avg Time (s) | Signature Acc | File Acc |\n"
    report += "|:------|:---------|:-----------|:-------------|:--------------|:---------|\n"
    
    for model in MODELS_TO_TEST:
        if model in model_metrics:
            m = model_metrics[model]
            report += f"| {model} | {m['accuracy']:.1f}% ({m['correct']}/{m['total']}) | {m['error_rate']:.1f}% | {m['avg_time']} | {m['signature_accuracy']:.1f}% | {m['file_accuracy']:.1f}% |\n"
    
    report += "\n## Detailed Results by Model\n\n"
    
    for model in MODELS_TO_TEST:
        if model not in by_model:
            continue
            
        report += f"### {model}\n\n"
        report += "| Question | Judgment | Answer | Time |\n"
        report += "|:---------|:---------|:-------|:-----|\n"
        
        for r in by_model[model]:
            q = r["question"].replace("|", "\\|")[:50]
            j = r.get("judgment", "N/A")
            a = r["agent_answer"].replace("|", "\\|").replace("\n", " ")[:60]
            t = r.get("time_seconds", 0)
            report += f"| {q} | {j} | {a} | {t}s |\n"
        
        report += "\n"
    
    return report

async def main():
    # Load dataset
    if not os.path.exists(DATASET_FILEPATH):
        print(f"Error: {DATASET_FILEPATH} not found. Run generate_dataset.py first.")
        return
    
    with open(DATASET_FILEPATH, "r") as f:
        dataset = json.load(f)
    
    print(f"Loaded {len(dataset)} questions")
    print(f"Models to test: {', '.join(MODELS_TO_TEST)}")
    
    # Create results directory
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Run evaluation for each model
    all_results = []
    for model in MODELS_TO_TEST:
        try:
            results = await run_agent_with_model(model, dataset)
            all_results.extend(results)
            
            # Save intermediate results
            with open(f"{RESULTS_DIR}/results_{model}.json", "w") as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"\nError evaluating {model}: {e}")
            continue
    
    # Evaluate with judge
    print("\n" + "="*60)
    all_results = await evaluate_with_ollama_judge(all_results)
    
    # Save all results
    with open(f"{RESULTS_DIR}/all_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    # Generate report
    report = generate_comparison_report(all_results)
    
    with open("evaluation/multi_model_report.md", "w") as f:
        f.write(report)
    
    print("\n" + "="*60)
    print("✅ Multi-model evaluation complete!")
    print(f"Report saved to: evaluation/multi_model_report.md")
    print(f"Results saved to: {RESULTS_DIR}/")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
