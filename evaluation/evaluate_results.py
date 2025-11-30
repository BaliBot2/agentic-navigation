import json
import os
import asyncio
from dotenv import load_dotenv
from llama_index.llms.google_genai import GoogleGenAI
from tqdm import tqdm

RESULTS_FILEPATH = "evaluation/results.json"
REPORT_FILEPATH = "evaluation/report.md"

async def evaluate_results():
    load_dotenv()
    if not os.path.exists(RESULTS_FILEPATH):
        print(f"Error: {RESULTS_FILEPATH} not found.")
        return

    with open(RESULTS_FILEPATH, "r") as f:
        results = json.load(f)

    llm = GoogleGenAI(model_name="gemini-2.0-flash-exp")

    correct_count = 0
    total_count = len(results)
    
    evaluation_details = []

    print(f"Evaluating {total_count} results...")

    for item in tqdm(results):
        question = item["question"]
        ground_truth = item["ground_truth"]
        agent_answer = item["agent_answer"]
        
        prompt = f"""
        You are an impartial judge evaluating the correctness of an answer provided by an AI agent.
        
        Question: {question}
        Ground Truth: {ground_truth}
        Agent Answer: {agent_answer}
        
        Is the Agent Answer correct based on the Ground Truth? 
        Consider semantic equivalence. If the agent says "I don't know" or "Error", it is incorrect.
        If the ground truth is a file path, allow for relative/absolute path differences.
        If the ground truth is a signature, allow for minor formatting differences.
        
        Respond with ONLY "CORRECT" or "INCORRECT".
        """
        
        try:
            response = await llm.acomplete(prompt)
            judgment = response.text.strip().upper()
        except Exception as e:
            print(f"Error evaluating item: {e}")
            judgment = "ERROR"

        is_correct = "CORRECT" in judgment
        if is_correct:
            correct_count += 1
            
        evaluation_details.append({
            "question": question,
            "ground_truth": ground_truth,
            "agent_answer": agent_answer,
            "judgment": judgment
        })

    # Metrics Calculation
    error_count = sum(1 for item in evaluation_details if "Error" in item['agent_answer'] or item['judgment'] == "ERROR")
    # Incorrect = questions that were answered (no error) but judged incorrect
    incorrect_count = sum(1 for item in evaluation_details if "Error" not in item['agent_answer'] and item['judgment'] != "ERROR" and not ("CORRECT" in item['judgment']))
    
    accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
    error_rate = (error_count / total_count) * 100 if total_count > 0 else 0
    
    # Generate Report
    report_content = f"# Evaluation Report\n\n"
    report_content += "## Summary Metrics\n\n"
    report_content += f"- **Total Questions:** {total_count}\n"
    report_content += f"- **Accuracy:** {accuracy:.2f}% ({correct_count}/{total_count})\n"
    report_content += f"- **Error Rate:** {error_rate:.2f}% ({error_count}/{total_count})\n"
    report_content += f"- **Correct:** {correct_count}\n"
    report_content += f"- **Incorrect:** {incorrect_count}\n"
    report_content += f"- **Errors:** {error_count}\n\n"
    
    report_content += "## Detailed Results\n\n"
    report_content += "| Question | Judgment | Agent Answer | Ground Truth |\n"
    report_content += "| :--- | :--- | :--- | :--- |\n"
    
    for item in evaluation_details:
        # Escape pipes in markdown table
        q = item['question'].replace("|", "\|")
        j = item['judgment']
        a = item['agent_answer'].replace("|", "\|").replace("\n", " ")[:100] # Truncate long answers
        g = str(item['ground_truth']).replace("|", "\|").replace("\n", " ")[:100]
        report_content += f"| {q} | {j} | {a} | {g} |\n"

    with open(REPORT_FILEPATH, "w") as f:
        f.write(report_content)
        
    print(f"Evaluation complete. Accuracy: {accuracy:.2f}%. Report saved to {REPORT_FILEPATH}")

if __name__ == "__main__":
    asyncio.run(evaluate_results())
