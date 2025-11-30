import os
import json
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent

# -------------------- Config --------------------
REPO_PATH = r"./libpng"
CODE_STRUCT_FILEPATH = "code_structure.json"
OLLAMA_MODEL = "llama3.2"  # Change to your preferred model

# -------------------- Setup --------------------
Settings.llm = Ollama(model=OLLAMA_MODEL, request_timeout=120.0)

print(f"✅ Using Ollama model: {OLLAMA_MODEL}")

# -------------------- Load code map --------------------
try:
    with open(CODE_STRUCT_FILEPATH, "r") as f:
        code_map_data = json.load(f)
    print("🗺️  Code map loaded successfully.")
except FileNotFoundError:
    print("❌ ERROR: code structure unavailable")
    raise SystemExit(1)

# -------------------- Tools --------------------
def get_code_map_info(query: str) -> str:
    """
    Look up a section in code_structure.json by key: 'code_map', 'file_dependencies', or 'call_map'.
    """
    if query in code_map_data:
        return json.dumps(code_map_data[query], indent=2)
    return "Invalid query. Available keys are 'code_map', 'file_dependencies', 'call_map'."

def read_source_file(filename: str) -> str:
    """
    Read a source file from the repo, e.g., 'pngread.c' or 'contrib/visupng/VisualPng.c'.
    """
    filepath = os.path.normpath(os.path.join(REPO_PATH, filename))
    if not filepath.startswith(os.path.normpath(REPO_PATH)):
        return "Error: Access to this file path is not allowed."
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."

# -----------------------Tool loading-------------------------------------
tool_get_map_info = FunctionTool.from_defaults(fn=get_code_map_info)
tool_read_file = FunctionTool.from_defaults(fn=read_source_file)

# -------------------- Agent --------------------
ollama_agent = ReActAgent(
    tools=[tool_get_map_info, tool_read_file],
    llm=Settings.llm,
    verbose=True,
)

print("✅ Ollama agent is ready.")
