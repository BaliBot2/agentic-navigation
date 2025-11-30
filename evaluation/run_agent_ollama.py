import json
import os
import sys
import asyncio
from tqdm import tqdm

# Add parent directory to path to import agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_ollama import ollama_agent as agent

DATASET_FILEPATH = "evaluation/dataset.json"
RESULTS_FILEPATH = "evaluation/results.json"

async def run_agent_eval():
    if not os.path.exists(DATASET_FILEPATH):
        print(f"Error: {DATASET_FILEPATH} not found.")
        return

    with open(DATASET_FILEPATH, "r") as f:
        dataset = json.load(f)

    results = []
    
    print(f"Running evaluation on {len(dataset)} items...")
    
    for item in tqdm(dataset):
        question = item["question"]
        
        try:
            # Run agent
            handler = agent.run(question)
            response = await handler
            
            # Extract answer - try multiple methods
            answer = None
            
            # Method 1: response attribute
            if hasattr(response, 'response') and response.response:
                answer = str(response.response)
            
            # Method 2: message.content
            if not answer and hasattr(response, 'message'):
                msg = response.message
                if hasattr(msg, 'content') and msg.content:
                    answer = str(msg.content)
            
            # Method 3: Direct string
            if not answer:
                answer = str(response)
                
        except Exception as e:
            answer = f"Error: {str(e)}"
        
        results.append({
            "question": question,
            "ground_truth": item["ground_truth"],
            "agent_answer": answer,
            "type": item["type"]
        })

    with open(RESULTS_FILEPATH, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Saved results to {RESULTS_FILEPATH}")

if __name__ == "__main__":
    asyncio.run(run_agent_eval())
