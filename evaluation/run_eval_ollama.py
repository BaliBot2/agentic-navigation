import os
import subprocess
import sys

def get_python_executable():
    # Check for local venv
    venv_python = os.path.join(os.getcwd(), "venv", "bin", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

def run_script(script_name):
    print(f"--- Running {script_name} ---")
    python_exe = get_python_executable()
    print(f"Using Python: {python_exe}")
    result = subprocess.run([python_exe, script_name], cwd=os.getcwd())
    if result.returncode != 0:
        print(f"Error running {script_name}. Exit code: {result.returncode}")
        sys.exit(result.returncode)
    print(f"--- Finished {script_name} ---\n")

def main():
    # 1. Generate Dataset
    run_script("evaluation/generate_dataset.py")
    
    # 2. Run Agent (with Ollama)
    run_script("evaluation/run_agent_ollama.py")
    
    # 3. Evaluate Results with Ollama
    run_script("evaluation/evaluate_with_ollama.py")
    
    print("Full evaluation pipeline complete (Ollama version).")
    print("Check evaluation/report_ollama.md for details.")

if __name__ == "__main__":
    main()
