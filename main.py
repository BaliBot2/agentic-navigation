import os
import json
import asyncio
from dotenv import load_dotenv
import datetime
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core import Settings
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.agent.workflow import AgentStream, ToolCallResult

# -------------------- Config --------------------
REPO_PATH = r".\libpng"
CODE_STRUCT_FILEPATH = "code_structure.json"

# -------------------- Setup --------------------
load_dotenv()
if os.getenv("GEMINI_API_KEY") is None:
    raise ValueError("API KEY error")

Settings.llm = GoogleGenAI(model_name="gemini-2.5-flash")
Settings.embed_model = GoogleGenAIEmbedding(model_name="text-embedding-004")

print("✅API key,repo, LLM and EM loaded")

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
#----------------------------------Basic summarization function due to excessive logging-----------------------------------------

#-----------------------Tool loading-------------------------------------
tool_get_map_info = FunctionTool.from_defaults(fn=get_code_map_info)
tool_read_file = FunctionTool.from_defaults(fn=read_source_file)

# -------------------- Agent --------------------
agent = ReActAgent(tools=[tool_get_map_info, tool_read_file],
    llm=Settings.llm,
    verbose=True,  
)

print("✅ Agent is ready.")

# -------------------- Streaming run --------------------
async def run_once(prompt: str):
    # --- Create a log file ---
    log_filename = f"agent_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    print(f"📝 Saving conversation to {log_filename}")

    with open(log_filename, 'w', encoding='utf-8') as log_file:
        # --- Write  to the log ---
        log_file.write(f"User Query: {prompt}\n\n")
        log_file.write("--- Agent's Thought Process ---\n")

        handler = agent.run(prompt)  # returns a streaming handler
        
        # --- Create a buffer to cleanly log ---
        stream_buffer = ""

        # Stream intermediate events
        async for ev in handler.stream_events():
            if isinstance(ev, ToolCallResult):
                # console printer
                print(f"\n🔧 Tool Result: {ev.tool_name}")


                # ---Write the tool results ---
                log_file.write(f"\n🔧 Tool Result: {ev.tool_name}\n")


            if isinstance(ev, AgentStream):
                # stylistic
                print(ev.delta, end="", flush=True)
                
                # add text to buffer
                stream_buffer += ev.delta

        # --- write complete buffered stream to log ---
        log_file.write(stream_buffer)

        # Await the final response object
        response = await handler
        
        print("\n\nFinal Answer:\n", str(response))
        log_file.write("\n\n--- Final Answer ---\n")
        log_file.write(str(response))

if __name__ == "__main__":
    prompt = "What is the full function signature for png_get_cHRM?"
    asyncio.run(run_once(prompt))
