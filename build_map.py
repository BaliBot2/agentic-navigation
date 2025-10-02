import os
import json
import subprocess
import re
from graphviz import Digraph # Import the new library

# --- (The functions generate_code_map, generate_file_dependencies, 
# --- Part 1: Generate the Code Map (Function Definitions) ---

def generate_code_map(repo_path="."):
    """
    Uses ctags to generate a classic 'tags' file and then parses it with Python.
    This is more compatible than relying on the JSON output format.
    """
    print("🗺️  Generating Code Map with ctags...")
    tags_filename = "tags"
    
    # Command to generate the classic, tab-separated tags file
    ctags_command = [
        "ctags",
        "-R",
        "--fields=+S",
        "--c-kinds=f",
        f"-o", # Specify the output file
        tags_filename
    ]
    
    try:
        # Run the command. We add a timeout and check for errors.
        process = subprocess.run(
            ctags_command, 
            capture_output=True, 
            text=True, 
            cwd=repo_path,
            timeout=30, # Add a timeout in case it hangs
            check=True  # This will raise an exception if ctags returns a non-zero exit code
        )
    except FileNotFoundError:
        print("❌ CRITICAL ERROR: 'ctags' command not found. Make sure it's installed and in your PATH.")
        return {}
    except subprocess.CalledProcessError as e:
        print(f"❌ CRITICAL ERROR: 'ctags' failed with exit code {e.returncode}.")
        print(f"   Stderr: {e.stderr}")
        return {}
    except subprocess.TimeoutExpired:
        print("❌ CRITICAL ERROR: 'ctags' command timed out.")
        return {}

    # Now, parse the generated 'tags' file
    definitions = {}
    try:
        with open(os.path.join(repo_path, tags_filename), 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('!_'):  # Skip header lines
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue
                
                func_name = parts[0]
                file_path = parts[1]
                # The line number is in the pattern part, e.g., /.../;$"
                pattern = parts[2] 
                
                # Find the line number using a simple regex
                line_search = re.search(r'(\d+)', pattern)
                line_num = int(line_search.group(1)) if line_search else 'N/A'

                # Find the signature
                signature = ""
                for field in parts[3:]:
                    if field.startswith('signature:'):
                        signature = f"{func_name}{field.replace('signature:', '')}"
                        break
                
                definitions[func_name] = {
                    "file": file_path,
                    "line": line_num,
                    "signature": signature if signature else func_name
                }
    except FileNotFoundError:
        print(f"❌ ERROR: Could not find the generated '{tags_filename}' file to parse.")
        return {}
    finally:
        # Clean up the tags file
        if os.path.exists(os.path.join(repo_path, tags_filename)):
            os.remove(os.path.join(repo_path, tags_filename))

    print(f"✅ Found {len(definitions)} function definitions.")
    return definitions
# --- Part 2: Generate the File Dependency Graph ---

def generate_file_dependencies(repo_path="."):
    """
    Uses ripgrep to find all #include dependencies.
    """
    print("🔗 Generating File Dependency Graph with ripgrep...")
    rg_command = [
        "rg",
        "--json",
        "--type", "c",  # Search C-like files
        '--regexp', r'^#include\s*["<](.*)[">]'
    ]
    
    process = subprocess.run(rg_command, capture_output=True, text=True, cwd=repo_path)

    if process.returncode != 0 and process.returncode != 1: # rg returns 1 if no matches found
        print("Error running ripgrep for includes:", process.stderr)
        return {}

    dependencies = {}
    for line in process.stdout.strip().split('\n'):
        try:
            match = json.loads(line)
            if match.get("type") == "match":
                file_path = match["data"]["path"]["text"]
                # Extract the included file from the match text
                included_file = match["data"]["submatches"][0]["match"]["text"]
                
                if file_path not in dependencies:
                    dependencies[file_path] = []
                dependencies[file_path].append(included_file)
        except (json.JSONDecodeError, KeyError):
            continue
            
    print(f"✅ Found dependencies for {len(dependencies)} files.")
    return dependencies


def generate_call_graph(repo_path, function_definitions):
    """
    Uses ripgrep to approximate the call graph by searching for function names.
    This version is more robust and handles potential errors gracefully.
    """
    print("📞 Generating Call Graph (Approximation)...")
    
    # 1. ADD THIS CHECK: If ctags failed, we can't proceed.
    if not function_definitions:
        print("⚠️  Cannot generate call graph because function definitions are missing (ctags failed).")
        return {}

    all_known_functions = list(function_definitions.keys())
    
    function_pattern = r'\b(' + '|'.join(re.escape(f) for f in all_known_functions) + r')\b'

    rg_command = [
        "rg", "--json", "--type", "c", '--regexp', function_pattern,
    ]

    process = subprocess.run(rg_command, capture_output=True, text=True, cwd=repo_path)
    
    if process.returncode != 0 and process.returncode != 1:
        print("Error running ripgrep for call graph:", process.stderr)
        return {}

    file_to_calls = {}
    for line in process.stdout.strip().split('\n'):
         try:
            match = json.loads(line)
            if match.get("type") == "match":
                line_text_before_paren = match["data"]["lines"]["text"].strip().split('(')[0]
                
                # 2. ADD THIS CHECK: Ensure there's something to split before getting the last item.
                words = line_text_before_paren.split()
                if not words:
                    continue # Skip empty or malformed lines

                called_function = words[-1]
                
                if called_function not in all_known_functions:
                    continue

                file_path = match["data"]["path"]["text"]
                if file_path not in file_to_calls:
                    file_to_calls[file_path] = set()
                
                func_def = function_definitions.get(called_function)
                if not (func_def and func_def["file"] == file_path and func_def["line"] == match["data"]["line_number"]):
                    file_to_calls[file_path].add(called_function)

         except (json.JSONDecodeError, KeyError, IndexError):
            # Catch any potential errors from malformed lines and continue
            continue

    for file_path in file_to_calls:
        file_to_calls[file_path] = sorted(list(file_to_calls[file_path]))

    print(f"✅ Found function calls in {len(file_to_calls)} files.")
    return file_to_calls

# --- Visualization Functions ---

def visualize_dependencies(dependency_data, output_filename="file_dependencies"):
    """
    Creates a high-resolution SVG diagram of the file dependencies,
    filtering out common system headers to reduce noise.
    """
    print("🎨 Visualizing file dependencies (High-Res SVG)...")
    
    # List of common C standard library headers to ignore
    ignore_list = {
        "stdio.h", "string.h", "stdlib.h", "stdarg.h", "ctype.h",
        "math.h", "setjmp.h", "time.h", "zlib.h", "png.h", "pngconf.h"
    }

    # Use the 'fdp' engine for a more spread-out layout
    dot = Digraph(comment='File Dependencies', engine='fdp')
    dot.attr('node', shape='box', style='rounded')
    dot.attr(overlap='false', splines='true') # Attributes to reduce overlaps

    # Collect all relevant nodes first
    all_files = set()
    for file, includes in dependency_data.items():
        if file not in ignore_list:
            all_files.add(file)
            for included_file in includes:
                if included_file not in ignore_list:
                    all_files.add(included_file)
    
    for file in all_files:
        dot.node(file, file)

    # Add edges for non-ignored files
    for file, includes in dependency_data.items():
        if file in all_files:
            for included_file in includes:
                if included_file in all_files:
                    dot.edge(file, included_file)

    # Render to SVG with a higher DPI for better initial spacing
    dot.render(output_filename, format='svg', view=False, cleanup=True)
    print(f"✅ Saved scalable dependency graph to {output_filename}.svg")
# (Keep the rest of your script the same, just replace this function)

def visualize_call_map(call_map_data, code_map, output_filename="call_map", focus_file=None, focus_dir=None):
    """
    Creates a high-resolution SVG diagram of the call map.
    Can be filtered to a specific file or directory.
    """
    print(f"🎨 Visualizing call map for '{output_filename}'...")
    dot = Digraph(comment='File to Function Call Map')
    dot.attr(rankdir='TB', size='20,20', overlap='false', splines='true')

    filtered_calls = {}

    # Apply filters if provided
    if focus_file:
        if focus_file in call_map_data:
            filtered_calls[focus_file] = call_map_data[focus_file]
    elif focus_dir:
        for file_path, called_functions in call_map_data.items():
            # Use os.path.normpath to handle different slash types (\ vs /)
            if os.path.normpath(file_path).startswith(os.path.normpath(focus_dir)):
                filtered_calls[file_path] = called_functions
    else:
        # No filter, use the whole map (can be very large!)
        filtered_calls = call_map_data

    if not filtered_calls:
        print(f"⚠️ No call data found for the specified filter. Skipping visualization.")
        return

    # Add file nodes
    dot.attr('node', shape='box', style='rounded', color='blue')
    for file_path in filtered_calls.keys():
        dot.node(file_path, file_path)

    # Add function nodes, but only for functions that are actually called
    dot.attr('node', shape='ellipse', style='', color='black')
    all_called_functions = set()
    for functions in filtered_calls.values():
        all_called_functions.update(functions)
    
    for func in all_called_functions:
        dot.node(func, func)

    # Add edges
    for file_path, called_functions in filtered_calls.items():
        for func in called_functions:
            dot.edge(file_path, func)
            
    dot.render(output_filename, format='svg', view=False, cleanup=True)
    print(f"✅ Saved scalable call map to {output_filename}.svg")


# --- Main Execution Block (Updated Version) ---

# --- Main Execution Block (Corrected Filter Paths) ---

if __name__ == "__main__":
    # The C codebase is in the 'libpng' subfolder
    REPO_PATH = r".\libpng" 
    OUTPUT_FILE = "code_structure.json"

    # Generate the main data structures
    definitions = generate_code_map(REPO_PATH)
    dependencies = generate_file_dependencies(REPO_PATH)
    call_map = generate_call_graph(REPO_PATH, definitions)
    
    # --- Visualize the data in focused chunks ---
    
    # Visualize dependencies (this is usually manageable)
    if dependencies:
        visualize_dependencies(dependencies)

    # Visualize the call map, but for specific, smaller parts
    if call_map:
        # --- CORRECTED FILTER PATHS ---

        # Example 1: Visualize calls made ONLY by 'pngread.c'
        # The path should be relative to the REPO_PATH, not include it.
        visualize_call_map(call_map, definitions, 
                           output_filename="call_map_pngread", 
                           focus_file="pngread.c")

        # Example 2: Visualize calls made by files in the 'contrib/visupng' directory
        # The path here is also relative to the REPO_PATH.
        visualize_call_map(call_map, definitions, 
                           output_filename="call_map_visupng_module",
                           focus_dir=os.path.join("contrib", "visupng"))
        
    # --- Combine and save the full structure map ---
    print(f"\n🧩 Combining all structures into {OUTPUT_FILE}...")
    master_structure = {
        "code_map": definitions,
        "file_dependencies": dependencies,
        "call_map": call_map
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_structure, f, indent=2)
        
    print("🎉 Done! Your codebase map and FOCUSED visualizations are ready.")