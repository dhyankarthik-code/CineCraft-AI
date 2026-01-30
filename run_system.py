
# Start both the In-Game Agent and the Web UI
import subprocess
import time
import sys
import os

def main():
    print("Starting BBS AI Agent System...")
    
    # 1. Start In-Game Agent (Background)
    # Using Popen to keep it running
    print("[Launcher] Starting In-Game Agent (run_agent.py)...")
    agent_process = subprocess.Popen(
        [sys.executable, "-m", "src.run_agent"],
        cwd=os.getcwd(),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    time.sleep(2)
    
    # 2. Start Web UI (Foreground)
    print("[Launcher] Starting Web UI (app.py)...")
    # This will block until app.py exits
    subprocess.run([sys.executable, "app.py"], cwd=os.getcwd())
    
    # Cleanup
    print("[Launcher] Shutting down...")
    agent_process.terminate()

if __name__ == "__main__":
    main()
