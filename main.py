import platform
import subprocess
from google import genai
import os
from dotenv import load_dotenv
import sys

# Load environment variables from the script/exe directory
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, ".env")
# print(f"Looking for .env at: {dotenv_path}")  # Debug print
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(".env loaded from script directory")
else:
    # Fallback to Program Files directory if exe is in PATH
    program_files_path = r"C:\Program Files\SmartCMD\.env"
    # print(f"Fallback: Looking for .env at: {program_files_path}")  # Debug print
    if os.path.exists(program_files_path):
        load_dotenv(program_files_path)
        # print(".env loaded from Program Files")
    else:
        # Another fallback to current working directory
        cwd_dotenv = os.path.join(os.getcwd(), ".env")
        # print(f"Another fallback: Looking for .env at: {cwd_dotenv}")  # Debug print
        if os.path.exists(cwd_dotenv):
            load_dotenv(cwd_dotenv)
            # print(".env loaded from current working directory")
        else:
            print("No .env file found in script, Program Files, or current directory")

# Get the API key from environment
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    print("Error: GENAI_API_KEY not found. Please ensure .env file exists with the key.")
    sys.exit(1)

# Initialize GenAI client
client = genai.Client(api_key=api_key)
HISTORY_FILE = os.path.expanduser("~/.smartcmd_history")

#history
def log_history(query, command):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{query} --> {command}\n")

def detect_os():
    name = platform.system().lower()
    if "windows" in name:
        return "Windows"
    elif "linux" in name:
        return "Linux"
    elif "darwin" in name:
        return "macOS"
    else:
        return name

def ask_gemma(prompt, os_name):
    full_prompt = (
        f"You are an expert in terminal and shell commands.\n"
        f"The user is on {os_name}.\n"
        f"User request: '{prompt}'\n"
        f"If the user asks to open an app, respond with the full path command (like start C:\\Path\\App.exe, in this my %USERNAME% IS DELL).\n"
        f"If unsure, respond with a safe placeholder command (like echo Unable to determine command).\n"
        f"If the user asks about non-command topics (like a question, fact, joke, etc.), respond naturally in one short helpful message"
        f"Never output destructive or system-breaking commands (like delete system folders or registry edits)."
        f"When unsure, prefer to respond safely with: echo Unable to determine command."
        "Respond with only the exact command (no explanations, no extra text)."
    )
    response = client.models.generate_content(
        model="gemma-3-27b-it",
        contents=full_prompt
    )
    return response.text.strip()

def run_command(cmd):
    subprocess.run(cmd, shell=True)

def handle_open_command(user_input):
    app = user_input[5:].strip()
    if not app:
        print("Usage: open <appname>")
        return

    # Common app locations to search
    possible_paths = [
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", app, f"{app}.exe"),
        os.path.join("C:\\Program Files", app, f"{app}.exe"),
        os.path.join("C:\\Program Files (x86)", app, f"{app}.exe"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                print(f"Opening {app}...")
                os.startfile(path)
                return
            except Exception as e:
                print("Failed to open app:", e)
                return

    # If not found locally, fallback to AI
    print(f"App '{app}' not found locally. Asking AI...")
    try:
        os_name = detect_os()
        command = ask_gemma(f"open {app}", os_name)
        print(f"Suggested by AI: {command}")
        confirm = input("Run this command instead? [Y/n]: ").strip().lower()
        if confirm in ["", "y", "yes"]:
            run_command(command)
    except Exception as e:
        print("Error:", e)

def show_history():
    if os.path.exists(HISTORY_FILE):
        os.startfile(HISTORY_FILE)
    else:
        print("No history yet.")

def is_history_query(query):
    keywords = ["history", "past commands", "previous commands", "command log"]
    return any(k in query.lower() for k in keywords)        

def main():
    os_name = detect_os()
    print(f"Detected OS: {os_name}\n(Type 'exit' to quit)\n")

    while True:
        query = input("> ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        if not query:
            continue
        if query.lower() in ["exit", "quit"]:
            break

        if is_history_query(query):
            show_history()
            continue

        if query.lower().startswith("open "):
            handle_open_command(query)
            continue
        try:
            command = ask_gemma(query, os_name)
            log_history(query, command)
            print(f"Suggested: {command}")
            confirm = input("Run it? [Y/n]: ").strip().lower()
            if confirm in ["", "y", "yes"]:
                if command.startswith("start "):
                    print("Note: 'start' commands may not work for apps not in PATH. Use 'open <app>' instead.")
                run_command(command)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()
