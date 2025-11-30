import json
import os
import sys
import asyncio
from tqdm import tqdm

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import agent

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
        # Retry logic for 429 errors
        max_retries = 3
        retry_delay = 10
        
        for attempt in range(max_retries):
            try:
                # Run agent
                handler = agent.run(question)
                response = await handler
                
                # Robust extraction - handle multiple response formats
                answer = None
                
                # Try different extraction methods
                try:
                    # Method 1: Direct response attribute
                    if hasattr(response, 'response') and response.response:
                        answer = str(response.response)
                except Exception:
                    pass
                
                if not answer:
                    try:
                        # Method 2: ChatMessage with blocks
                        if hasattr(response, 'chat_message'):
                            chat_msg = response.chat_message
                            if hasattr(chat_msg, 'blocks') and chat_msg.blocks:
                                # Concatenate all text blocks
                                answer = " ".join(str(block.text) if hasattr(block, 'text') else str(block) for block in chat_msg.blocks)
                            elif hasattr(chat_msg, 'content'):
                                answer = str(chat_msg.content)
                    except Exception:
                        pass
                
                if not answer:
                    try:
                        # Method 3: Direct string conversion
                        answer = str(response)
                    except Exception as e:
                        answer = f"Error: Failed to extract response - {str(e)}"
                
                break # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "ResourceExhausted" in error_msg:
                    print(f"Rate limit hit. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                    answer = f"Error: {error_msg}" # Keep error if retries exhausted
                else:
                    answer = f"Error: {error_msg}"
                    break # Non-retriable error
        
        # Final safety delay
        await asyncio.sleep(5)
        
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
