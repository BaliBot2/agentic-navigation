import json
import os
import requests

RESULTS_FILEPATH = "evaluation/results.json"
REPORT_FILEPATH = "evaluation/report_ollama.md"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # Change this to your preferred model

def evaluate_with_ollama():
    if not os.path.exists(RESULTS_FILEPATH):
        print(f"Error: {RESULTS_FILEPATH} not found.")
        return

    with open(RESULTS_FILEPATH, "r") as f:
        results = json.load(f)

    correct_count = 0
    total_count = len(results)
    
    evaluation_details = []

    print(f"Evaluating {total_count} results using Ollama ({OLLAMA_MODEL})...")

    for i, item in enumerate(results):
        print(f"Evaluating {i+1}/{total_count}...", end=" ")
        
        question = item["question"]
        ground_truth = item["ground_truth"]
        agent_answer = item["agent_answer"]
        
        # Skip if agent had an error
        if "Error:" in agent_answer:
            judgment = "ERROR"
            is_correct = False
            print("ERROR")
        else:
            # Use Ollama to judge
            prompt = f"""You are an impartial judge evaluating the correctness of an answer.

Question: {question}
Ground Truth: {ground_truth}
Agent Answer: {agent_answer}

Is the Agent Answer correct based on the Ground Truth? 
Consider semantic equivalence. If the ground truth is a file path, allow for relative/absolute path differences.
If the ground truth is a signature, allow for minor formatting differences.

Respond with ONLY "CORRECT" or "INCORRECT"."""

            try:
                response = requests.post(
                    OLLAMA_API_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    judgment = response.json()["response"].strip().upper()
                    is_correct = "CORRECT" in judgment
                    print("CORRECT" if is_correct else "INCORRECT")
                else:
                    judgment = f"ERROR: Ollama returned {response.status_code}"
                    is_correct = False
                    print("ERROR")
                    
            except Exception as e:
                judgment = f"ERROR: {str(e)}"
                is_correct = False
                print("ERROR")

        if is_correct:
            correct_count += 1
            
        evaluation_details.append({
            "question": question,
            "ground_truth": ground_truth,
            "agent_answer": agent_answer,
            "judgment": judgment
        })

    # Metrics Calculation
    error_count = sum(1 for item in evaluation_details if "Error" in item['agent_answer'] or item['judgment'].startswith("ERROR"))
    incorrect_count = sum(1 for item in evaluation_details if "Error" not in item['agent_answer'] and not item['judgment'].startswith("ERROR") and not ("CORRECT" in item['judgment']))
    
    accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
    error_rate = (error_count / total_count) * 100 if total_count > 0 else 0
    
    # Calculate metrics by question type
    signature_questions = [item for item in evaluation_details if "signature" in item['question'].lower()]
    file_questions = [item for item in evaluation_details if "which file" in item['question'].lower()]
    
    signature_correct = sum(1 for item in signature_questions if "CORRECT" in item['judgment'])
    file_correct = sum(1 for item in file_questions if "CORRECT" in item['judgment'])
    
    signature_accuracy = (signature_correct / len(signature_questions) * 100) if signature_questions else 0
    file_accuracy = (file_correct / len(file_questions) * 100) if file_questions else 0
    
    # Generate Report
    report_content = f"# Evaluation Report (Ollama)\n\n"
    report_content += "## Summary Metrics\n\n"
    report_content += f"- **Total Questions:** {total_count}\n"
    report_content += f"- **Accuracy:** {accuracy:.2f}% ({correct_count}/{total_count})\n"
    report_content += f"- **Error Rate:** {error_rate:.2f}% ({error_count}/{total_count})\n"
    report_content += f"- **Correct:** {correct_count}\n"
    report_content += f"- **Incorrect:** {incorrect_count}\n"
    report_content += f"- **Errors:** {error_count}\n\n"
    
    report_content += "## Metrics by Question Type\n\n"
    report_content += f"- **Signature Questions:** {signature_accuracy:.2f}% ({signature_correct}/{len(signature_questions)})\n"
    report_content += f"- **File Lookup Questions:** {file_accuracy:.2f}% ({file_correct}/{len(file_questions)})\n\n"
    
    report_content += "## Detailed Results\n\n"
    report_content += "| Question | Judgment | Agent Answer | Ground Truth |\n"
    report_content += "| :--- | :--- | :--- | :--- |\n"
    
    for item in evaluation_details:
        q = item['question'].replace("|", "\\|")
        j = item['judgment']
        a = item['agent_answer'].replace("|", "\\|").replace("\n", " ")[:100]
        g = str(item['ground_truth']).replace("|", "\\|").replace("\n", " ")[:100]
        report_content += f"| {q} | {j} | {a} | {g} |\n"

    with open(REPORT_FILEPATH, "w") as f:
        f.write(report_content)
        
    print(f"\n✅ Evaluation complete!")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Report saved to {REPORT_FILEPATH}")

if __name__ == "__main__":
    evaluate_with_ollama()
