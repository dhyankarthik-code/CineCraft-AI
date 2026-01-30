import time
import os
import re
import sys
import requests
try:
    from .agent import BBSAgent
except ImportError:
    # Fallback if run directly (though -m is preferred)
    from agent import BBSAgent

def follow(thefile):
    """Generator to tail a file."""
    thefile.seek(0, 2) # Go to end
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def download_mod(query: str) -> str:
    """Download a mod OR shader from Modrinth."""
    try:
        # Determine type
        p_type = "shader" if "shader" in query.lower() else "mod"
        
        # 1. Search for project
        search_url = f"https://api.modrinth.com/v2/search?query={query}&facets=[[\"project_type:{p_type}\"]]&limit=1"
        r = requests.get(search_url)
        if r.status_code != 200 or not r.json()['hits']:
            return f"X {p_type.capitalize()} not found."
            
        project_id = r.json()['hits'][0]['project_id']
        title = r.json()['hits'][0]['title']
        
        # 2. Get version (1.20.1)
        versions_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        r_ver = requests.get(versions_url)
        versions = r_ver.json()
        
        if not versions:
            return f"Found '{title}' but no versions available."
        
        # Get first available file
        target_file = versions[0]['files'][0]
        file_url = target_file['url']
        filename = target_file['filename']
        
        # 3. Determine Target Directory
        # We are likely in project_root/src or project_root
        # Try to find server/mods
        if os.path.exists("server/mods"):
            base_dir = "server"
        elif os.path.exists("../server/mods"):
            base_dir = "../server"
        else:
            return "Error: Could not find server directory."

        if p_type == "shader":
            mod_dir = os.path.join(base_dir, "shaderpacks")
            success_msg = f"Downloaded Shader {title} to shaderpacks! Enable it in Video Settings."
        else:
            mod_dir = os.path.join(base_dir, "mods")
            success_msg = f"Installed Mod {title} to server/mods. RESTART server to apply."

        os.makedirs(mod_dir, exist_ok=True)
        
        with requests.get(file_url, stream=True) as stream:
            with open(os.path.join(mod_dir, filename), 'wb') as f:
                for chunk in stream.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        return success_msg
        
    except Exception as e:
        return f"Download error: {e}"

def main():
    print("BBS AI Agent Listener Starting...")
    
    # Path to server log
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(project_root, "server", "logs", "latest.log")
    
    if not os.path.exists(log_path):
        print(f"Error: Log file not found at {log_path}")
        if os.path.exists("server/logs/latest.log"):
            log_path = "server/logs/latest.log"
        else:
            return

    print(f"Monitoring log: {log_path}")

    # Initialize Agent
    agent = BBSAgent(
        minecraft_dir=os.path.join(project_root, "server")
    )
    
    # Verify RCON
    if not agent.rcon.is_available():
        print("Warning: RCON not available. Agent cannot reply in-game.")
    else:
        print("RCON Connected. Ready to reply.")
        agent.rcon.execute("say BBS Agent Online and Listening!")

    # Tail the log
    try:
        print(f"Opening log file: {log_path}")
        with open(log_path, "r", encoding='utf-8', errors='ignore') as logfile:
            print("Listening for '!agent' commands... (Tailing file)")
            for line in follow(logfile):
                # print(f"DEBUG: Read line: {line.strip()}") 
                if "!agent" in line and "<" in line and ">" in line:
                    print(f"DEBUG: Detected command in line: {line.strip()}")
                    match = re.search(r"<(\w+)> !agent (.+)", line)
                    match = re.search(r"<(\w+)> !agent (.+)", line)
                    if match:
                        player, instruction = match.groups()
                        print(f"Command received from {player}: {instruction}")
                        
                        agent.rcon.execute(f"say [Agent] Processing: {instruction}")
                        
                        try:
                            if instruction.strip().lower().startswith("install"):
                                # Extract query
                                query = instruction.strip()[7:].strip() # remove "install"
                                agent.rcon.execute(f"say [Agent] Searching Modrinth for '{query}'...")
                                result = download_mod(query)
                                agent.rcon.execute(f"say [Agent] {result}")
                            else:
                                # Get player position for context
                                pos_context = ""
                                try:
                                    pos_res = agent.rcon.execute("data get entity @p Pos")
                                    if pos_res.success:
                                        # Format: [123.45d, 64.0d, -789.0d]
                                        match = re.search(r'\[([-\d.]+)d?,\s*([-\d.]+)d?,\s*([-\d.]+)d?\]', pos_res.response)
                                        if match:
                                            x, y, z = match.groups()
                                            pos_context = f"PLAYER_POSITION: {x} {y} {z}\nCRITICAL: Spawn EVERYTHING relative to this position using relative coordinates (~) where possible."
                                            print(f"Player at: {x} {y} {z}")
                                except Exception as e:
                                    print(f"Failed to get position: {e}")

                                # For simple spawn commands, disable camera movements to prevent player teleportation
                                if any(word in instruction.lower() for word in ["spawn", "summon", "create"]) and len(instruction.split()) < 10:
                                    pos_context += "\n\nIMPORTANT: This is a SIMPLE spawn request. Do NOT include any camera movements or player teleports. Only spawn the entity at the player's location. Keep the scene minimal with just the spawn action."

                                storyboard = agent.process_script(instruction, custom_instructions=pos_context)
                                scene_count = len(storyboard.get('scenes', []))
                                agent.rcon.execute(f"say [Agent] Generated {scene_count} scenes. Executing...")
                                
                                agent.generate_commands()
                                
                                results = agent.execute_via_rcon(realtime=False)
                                success_count = sum(1 for r in results if r['success'])
                                agent.rcon.execute(f"say [Agent] Done. Executed {success_count} commands.")
                                
                        except Exception as e:
                            print(f"Error processing command: {e}")
                            import traceback
                            traceback.print_exc()
                            with open("agent_error.log", "w") as f:
                                traceback.print_exc(file=f)
                            agent.rcon.execute(f"say [Agent] Error: {str(e)}")

    except KeyboardInterrupt:
        print("Stopping listener.")

if __name__ == "__main__":
    main()
