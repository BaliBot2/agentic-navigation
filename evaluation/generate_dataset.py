import json
import random
import os

CODE_STRUCT_FILEPATH = "code_structure.json"
DATASET_FILEPATH = "evaluation/dataset.json"

def generate_dataset():
    if not os.path.exists(CODE_STRUCT_FILEPATH):
        print(f"Error: {CODE_STRUCT_FILEPATH} not found.")
        return

    with open(CODE_STRUCT_FILEPATH, "r") as f:
        data = json.load(f)

    dataset = []
    
    # 1. Questions about function signatures (from code_map)
    if "code_map" in data:
        code_map = data["code_map"]
        keys = list(code_map.keys())
        # Sample some keys to avoid overwhelming dataset
        sample_keys = random.sample(keys, min(1, len(keys)))
        
        for key in sample_keys:
            info = code_map[key]
            question = f"What is the signature of '{key}'?"
            ground_truth = info.get("signature", "Unknown")
            dataset.append({
                "type": "signature_lookup",
                "question": question,
                "ground_truth": ground_truth
            })
            
            question_file = f"In which file is '{key}' defined?"
            ground_truth_file = info.get("file", "Unknown")
            dataset.append({
                "type": "file_lookup",
                "question": question_file,
                "ground_truth": ground_truth_file
            })

    # 2. Questions about file dependencies (if available)
    # (Assuming file_dependencies structure based on typical output, but checking existence first)
    if "file_dependencies" in data:
        deps = data["file_dependencies"]
        keys = list(deps.keys())
        sample_keys = random.sample(keys, min(0, len(keys)))
        
        for key in sample_keys:
            question = f"What are the dependencies of file '{key}'?"
            ground_truth = str(deps[key])
            dataset.append({
                "type": "dependency_lookup",
                "question": question,
                "ground_truth": ground_truth
            })

    # Ensure evaluation directory exists
    os.makedirs(os.path.dirname(DATASET_FILEPATH), exist_ok=True)
    
    with open(DATASET_FILEPATH, "w") as f:
        json.dump(dataset, f, indent=2)
    
    print(f"Generated {len(dataset)} questions in {DATASET_FILEPATH}")

if __name__ == "__main__":
    generate_dataset()
