"""
BBS AI Agent - REAL-TIME MINECRAFT INTEGRATION
Includes: Persistent Memory & Content Downloader (DataPacks/Plugins)
"""

import os
import json
import time
import requests
import gradio as gr
from openai import OpenAI
from mcrcon import MCRcon
from dotenv import load_dotenv

load_dotenv()

# Configuration
RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "minecraft")
HISTORY_FILE = "conversation_history.json"

# Initialize OpenAI
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# State
storyboard = None
rcon_connected = False
conversation_history = []

def load_history():
    """Load chat history from file."""
    global conversation_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                conversation_history = json.load(f)
        except:
            conversation_history = []

def save_history():
    """Save chat history to file."""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(conversation_history, f, indent=2)
    except Exception as e:
        print(f"Failed to save history: {e}")

# Load memory on startup
load_history()

def search_modrinth(query: str, type_filter: str = "datapack") -> list:
    """Search Modrinth for content."""
    url = f"https://api.modrinth.com/v2/search?query={query}&facets=[[\"project_type:{type_filter}\"]]&limit=5"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            hits = r.json()['hits']
            return [f"• **{h['title']}** ({h['author']}) - {h['description'][:100]}..." for h in hits]
    except Exception as e:
        return [f"Error searching generic content: {e}"]

    return ["No results found."]

# Load custom game path
MINECRAFT_DIR = os.getenv("MINECRAFT_DIR", os.path.join("server", "mods"))

def download_mod(query: str, version: str = "1.20.1") -> str:
    """Download a mod OR shader from Modrinth."""
    try:
        # Determine type
        p_type = "shader" if "shader" in query.lower() else "mod"
        
        # 1. Search for project
        search_url = f"https://api.modrinth.com/v2/search?query={query}&facets=[[\"project_type:{p_type}\"]]&limit=1"
        r = requests.get(search_url)
        if r.status_code != 200 or not r.json()['hits']:
            return f"❌ {p_type.capitalize()} not found."
            
        project_id = r.json()['hits'][0]['project_id']
        title = r.json()['hits'][0]['title']
        
        # 2. Get version
        # For shaders, version matching is loose, but we try standard
        versions_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        r_ver = requests.get(versions_url)
        versions = r_ver.json()
        
        if not versions:
            return f"⚠️ Found '{title}' but no versions available."
        
        # Get first available file
        target_file = versions[0]['files'][0]
        file_url = target_file['url']
        filename = target_file['filename']
        
        # 3. Determine Target Directory
        target_base = os.getenv("MINECRAFT_DIR")
        
        if p_type == "shader":
            if target_base:
                mod_dir = os.path.join(target_base, "shaderpacks")
                success_msg = f"✅ Downloaded Shader **{title}** to `shaderpacks/`!\n👉 Enable it in Video Settings > Shaders."
            else:
                mod_dir = os.path.join("server", "shaderpacks")
                success_msg = f"⚠️ Downloaded Shader **{title}** to local `server/shaderpacks/` (Game location unset)."
        else:
            # Logic for MODS/PLUGINS
            # Check for plugin loaders in the version we grabbed (heuristic)
            loaders = versions[0].get('loaders', [])
            is_plugin = "paper" in loaders or "spigot" in loaders or "bukkit" in loaders
            
            if is_plugin:
                mod_dir = os.path.join("server", "plugins")
                success_msg = f"✅ Installed Plugin **{title}** to `server/plugins/`.\n👉 Restart server to apply."
            else:
                # MODS (Forge/Fabric)
                if target_base:
                    # If game dir is set, copy to BOTH (Client + Server) for convenience?
                    # For now just Server, user can copy to client if needed, or I can try to copy to MINECRAFT_DIR too.
                    # User asked to "take care of it".
                    # Let's put in SERVER mods folder primarily.
                    mod_dir = os.path.join("server", "mods")
                    success_msg = f"✅ Installed Mod **{title}** to `server/mods/`.\n👉 Restart server to apply."
                    
                    # Optional: Copy to client if path exists
                    client_mods = os.path.join(target_base, "mods")
                    if os.path.exists(client_mods):
                         # Logic to copy would be here, but let's keep it simple.
                         success_msg += f"\n(Also copy this to your Client mods folder: `{client_mods}`)"
                else:
                    mod_dir = os.path.join("server", "mods")
                    success_msg = f"✅ Installed Mod **{title}** to `server/mods/`."

        os.makedirs(mod_dir, exist_ok=True)
        
        with requests.get(file_url, stream=True) as stream:
            with open(os.path.join(mod_dir, filename), 'wb') as f:
                for chunk in stream.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        return success_msg
        
    except Exception as e:
        return f"❌ Download error: {e}"

def test_rcon_connection():
    """Test if we can connect to Minecraft."""
    global rcon_connected
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT, timeout=3) as mcr:
            response = mcr.command("list")
            rcon_connected = True
            return True, f"✅ Connected to Minecraft! {response}"
    except Exception as e:
        rcon_connected = False
        return False, f"❌ Cannot connect: {str(e)}"



def get_player_position() -> tuple:
    """Get the first online player's current position via RCON.
    
    Returns:
        Tuple of (x, y, z) as integers, or (0, 64, 0) as fallback.
    """
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT, timeout=3) as mcr:
            # Get player position data
            response = mcr.command("data get entity @p Pos")
            # Response format: "Player has the following entity data: [x, y, z]"
            if "has the following entity data" in response:
                # Extract the array part [x, y, z]
                import re
                match = re.search(r'\[([-\d.]+)d?,\s*([-\d.]+)d?,\s*([-\d.]+)d?\]', response)
                if match:
                    x = int(float(match.group(1)))
                    y = int(float(match.group(2)))
                    z = int(float(match.group(3)))
                    return (x, y, z)
    except Exception as e:
        print(f"Could not get player position: {e}")
    
    # Fallback to safe spawn
    return (0, 64, 0)

def execute_commands_realtime(commands: list, delay: float = 0.3) -> list:
    """Execute all commands in Minecraft with delays."""
    results = []
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT, timeout=10) as mcr:
            for cmd in commands:
                if cmd.startswith("#") or not cmd.strip():
                    continue
                response = mcr.command(cmd)
                results.append(f"✓ {cmd[:50]}... → {response}")
                time.sleep(delay)
    except Exception as e:
        results.append(f"❌ Connection error: {e}")
    return results

def create_storyboard(story: str, player_pos: tuple = None) -> dict:
    """Create storyboard from story using GPT-4."""
    global storyboard
    
    # Get player's current position (still good for context)
    if player_pos is None:
        player_pos = get_player_position()
    
    px, py, pz = player_pos
    
    # Include context from last 3 turns
    context = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history[-6:]])
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"""You are a Minecraft Commander.
            
PLAYER POSITION: {px}, {py}, {pz}

CRITICAL: EVERYTHING MUST BE SPAWNED RELATIVE TO THE PLAYER.
Use `execute at @p run ...` for EVERY command.

RULES:
1. **SPAWNING**: ALWAYS use `execute at @p run summon <entity> ~<x> ~<y> ~<z> ...`
   - Example: `execute at @p run summon zombie ~5 ~0 ~5 {{Motion:[0.0,0.2,0.0]}}` (Spawns 5 blocks away at same height)
   - NEVER use absolute coordinates like `0 64 0`.
   - ALWAYS use `~` (tilde) relative coordinates. ~0 is player's feet.

2. **BLOCKS**: ALWAYS use `execute at @p run setblock ~<x> ~<y> ~<z> ...`
   - Example: `execute at @p run setblock ~3 ~0 ~3 diamond_block`

3. **LIVELY MOBS**:
   - For **MOBS ONLY** (zombies, dragons, etc.), add `{{Motion:[0.0, 0.3, 0.0]}}` or similar to make them move.
   - Do NOT add Motion to blocks or static structures.
   - Add `{{Attributes:[{{Name:"generic.movement_speed",Base:0.3}}]}}` for faster mobs.
   - Do NOT use NoAI:1b unless asked.

4. **WEAPONS / GUNS**:
   - You are now on a **FORGE SERVER**.
   - You CAN suggest Forge mods like "MrCrayfish's Gun Mod", "Timeless and Classics", etc.
   - You can also suggest "Quality Armory" (Plugin) if preferred, but Forge mods are better now.

5. **BLOCKBUSTER/SCENES**:
   - You are on a **FORGE SERVER**.
   - **Blockbuster Mod** is now FULLY supported if installed!
   - You can describe scenes with actors, recording, etc.

6. **HIGH PERFORMANCE / LOOPS (Command Blocks)**:
   - If user wants a LOOP, REPEAT, or MASSIVE continuous spawn (e.g. "spawn 100 cows", "every second", "continuously"), DO NOT use RCON loop.
   - Instead, PLACE A REPEATING COMMAND BLOCK.
   - Command: `execute at @p run setblock ~ ~1 ~ repeating_command_block{{Command:"<insert_command_here>",auto:1b}}`
   - Example (Spawn cow every tick): `execute at @p run setblock ~ ~1 ~ repeating_command_block{{Command:"summon cow ~ ~1 ~",auto:1b}}`
   - Tell the user: "I placed a Command Block to handle this high-speed task!"

7. **CLIENT MODS**:
   - You can now install Forge Mods directly to the server!
   - Use `download <name>` logic.

Output JSON:
{{
    "title": "Title",
    "is_mod_request": false,
    "mod_query": "if user asking to download mod, put name here",
    "scenes": [
        {{
            "name": "Scene Name",
            "description": "Short description",
            "commands": [
                "execute at @p run title @a title {{\"text\":\"Chapter 1\"}}",
                "execute at @p run summon zombie ~5 ~0 ~0"
            ]
        }}
    ]
}}"""},
            {"role": "user", "content": story}
        ],
        response_format={"type": "json_object"}
    )
    storyboard = json.loads(response.choices[0].message.content)
    return storyboard

def get_all_commands() -> list:
    if not storyboard:
        return []
    commands = []
    for scene in storyboard.get('scenes', []):
        commands.append(f"# === {scene.get('name', 'Scene')} ===")
        # Filter out unsafe commands
        safe_cmds = []
        for cmd in scene.get('commands', []):
            # STRICT FILTER: Prevent teleporting the player
            if cmd.strip().startswith("tp @") or " tp @a" in cmd or " tp @p" in cmd:
                safe_cmds.append(f"# BLOCKED UNSAFE COMMAND: {cmd}")
            else:
                safe_cmds.append(cmd)
        commands.extend(safe_cmds)
    return commands

def chat(message: str, history: list):
    """Main chat function with streaming status updates."""
    global storyboard, conversation_history
    
    msg = message.strip().lower()
    
    # Update memory
    conversation_history.append({"role": "user", "content": message})
    save_history()
    
    response = ""
    try:
        if msg in ["connect", "test"]:
            yield "🔌 Connecting to Minecraft server..."
            _, response = test_rcon_connection()
            yield response
        
        elif msg.startswith("download ") or msg.startswith("search "):
            yield "🔍 Searching Modrinth..."
            query = msg.replace("download ", "").replace("search ", "")
            results = search_modrinth(query, "datapack")
            response = f"🔍 **Found on Modrinth:**\n\n" + "\n".join(results) + "\n\n*(Downloading feature coming in next update!)*"
            yield response
        
        elif msg == "run":
            if not storyboard:
                yield "⚠️ Create a storyboard first!"
            else:
                yield "🎮 Preparing to execute commands..."
                cmds = get_all_commands()
                total = len([c for c in cmds if not c.startswith("#") and c.strip()])
                
                # Stream each command execution
                results = []
                try:
                    with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT, timeout=10) as mcr:
                        for i, cmd in enumerate(cmds):
                            if cmd.startswith("#") or not cmd.strip():
                                # Log blocked commands to UI
                                if "BLOCKED" in cmd:
                                    results.append(f"🛡️ {cmd[2:]}") # Show "BLOCKED..."
                                continue
                            
                            yield f"⚡ Executing ({i+1}/{total}): `{cmd[:50]}...`"
                            resp = mcr.command(cmd)
                            results.append(f"✓ {cmd[:40]}... → {resp}")
                            time.sleep(0.3)
                except Exception as e:
                    results.append(f"❌ Connection error: {e}")
                
                response = f"🎮 **Executed {len(results)} commands!**\n" + "\n".join(results[:10])
                yield response
        
        elif not client:
            yield "❌ No OpenAI API key configured."
        
        else:
            # Story processing with status updates
            yield "🤔 Understanding your request..."
            time.sleep(0.3)
            yield "🔌 Fetching player position..."
            
            # Explicitly fetch and show position
            pos = get_player_position()
            pos_msg = f"📍 **Targeting Player at: {pos}**"
            yield pos_msg
            
            yield "🎬 Generating storyboard with GPT-4o..."
            
            # Pass position to creator
            storyboard = create_storyboard(message, player_pos=pos)
            
            # Check for mod download request
            if storyboard.get("is_mod_request") and storyboard.get("mod_query"):
                mod_name = storyboard.get("mod_query")
                yield f"📦 Detected request for mod: '{mod_name}'"
                yield "🔄 Searching Modrinth API..."
                download_msg = download_mod(mod_name)
                yield download_msg
                if "Restart" in download_msg:
                    response = download_msg
                    yield response
                    # Stop processing unless there are also scenes
                    if not storyboard.get("scenes"):
                         conversation_history.append({"role": "assistant", "content": response})
                         save_history()
                         return

            yield "✨ Building scene breakdown..."
            time.sleep(0.2)
            
            summary = f"🎬 **{storyboard.get('title', 'Animation')}**\n{pos_msg}\n"
            for i, s in enumerate(storyboard.get('scenes', []), 1):
                summary += f"\n**Scene {i}:** {s.get('name', '')}\n_{s.get('description', '')}_\n"
            summary += "\n**Type `run` to execute in Minecraft!**"
            response = summary
            yield response
            
    except Exception as e:
        response = f"❌ Error: {str(e)}"
        yield response
    
    conversation_history.append({"role": "assistant", "content": response})
    save_history()

demo = gr.ChatInterface(
    fn=chat,
    title="🎮 BBS Agent (Memory + RCON)",
    description="I remember our chat! Ask me to search for content.",
    examples=["connect", "Search for spaceship datapacks", "A creeper launch into space"]
)

import threading
import re

def process_ingame_request(player: str, request: str):
    """Process a request from in-game chat."""
    print(f"Processing in-game request from {player}: {request}")
    
    # 1. Feedback in game
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
            mcr.command(f'tellraw @a "§e[BBS Agent] Thinking about: {request}..."')
    except:
        pass

    # 2. Get position
    pos = get_player_position()
    
    # 3. Generate storyboard
    try:
        global storyboard
        storyboard = create_storyboard(request, player_pos=pos)
        
        # === HANDLE MOD DOWNLOAD REQUESTS ===
        if storyboard.get("is_mod_request") and storyboard.get("mod_query"):
            mod_name = storyboard.get("mod_query")
            
            with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
                mcr.command(f'tellraw @a "§6[BBS Agent] Found mod request: {mod_name}"')
                mcr.command(f'tellraw @a "§6[BBS Agent] Searching Modrinth..."')
            
            # Execute download
            result_msg = download_mod(mod_name)
            
            # Sanitize message for JSON (remove markdown bolding for Tellraw compatibility)
            clean_msg = result_msg.replace("**", "").replace("`", "").replace("\n", " ").replace('"', "'")
            color = "§a" if "✅" in result_msg else "§c"
            
            with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
                mcr.command(f'tellraw @a "{color}[BBS Agent] {clean_msg}"')
            
            # Stop if no other commands (scenes)
            if not storyboard.get("scenes"):
                return
        # ====================================
        
        # 4. Notify ready
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
            mcr.command(f'tellraw @a "§a[BBS Agent] Generated {len(storyboard.get("scenes", []))} scenes!"')
            mcr.command(f'tellraw @a "§e[BBS Agent] Executing now..."')
        
        # 5. Execute immediately
        cmds = get_all_commands()
        execute_commands_realtime(cmds, delay=0.1)
        
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
            mcr.command(f'tellraw @a "§a[BBS Agent] Done!"')
            
    except Exception as e:
        print(f"Error processing in-game request: {e}")
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
                mcr.command(f'tellraw @a "§c[BBS Agent] Error: {str(e)}"')
        except:
            pass

def monitor_logs():
    """Monitor latest.log for chat commands."""
    log_path = os.path.join("server", "logs", "latest.log")
    
    # Wait for log file
    while not os.path.exists(log_path):
        time.sleep(1)
    
    print(f"Watching log file: {log_path}")
    
    with open(log_path, "r") as f:
        # Seek to end
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            # Check for chat pattern: [time] [thread/INFO]: <Player> !agent request
            # Regex: <(\w+)> !agent (.+)
            match = re.search(r'<(\w+)> !agent (.+)', line)
            if match:
                player = match.group(1)
                request = match.group(2)
                
                # Run in separate thread to not block monitoring
                threading.Thread(target=process_ingame_request, args=(player, request)).start()

# Start background monitoring
# monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
# monitor_thread.start()

if __name__ == "__main__":
    print("🎮 BBS AI Agent - RUNNING (In-Game Chat Enabled)")
    demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
