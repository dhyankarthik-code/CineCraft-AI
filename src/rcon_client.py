"""
Minecraft RCON Client for BBS AI Agent

Handles remote command execution to Minecraft via RCON protocol.
Falls back to alternative methods if RCON is not available.
"""

import os
import time
import socket
from typing import Optional, List, Tuple
from dataclasses import dataclass

try:
    from mcrcon import MCRcon
    MCRCON_AVAILABLE = True
except ImportError:
    MCRCON_AVAILABLE = False
    print("Warning: mcrcon not installed. RCON features disabled.")

from dotenv import load_dotenv

load_dotenv()


@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    response: str
    tick: int = 0
    command: str = ""


class MinecraftRCON:
    """
    RCON client for Minecraft command execution.
    
    Features:
    - Connection management with auto-reconnect
    - Command queuing and sequencing
    - Timing support for tick-based commands
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        password: str = None,
        timeout: float = 5.0
    ):
        """
        Initialize RCON client.
        
        Args:
            host: Minecraft server host (default: from env RCON_HOST)
            port: RCON port (default: from env RCON_PORT)  
            password: RCON password (default: from env RCON_PASSWORD)
            timeout: Connection timeout in seconds
        """
        self.host = host or os.getenv("RCON_HOST", "localhost")
        self.port = int(port or os.getenv("RCON_PORT", 25575))
        self.password = password or os.getenv("RCON_PASSWORD", "")
        self.timeout = timeout
        self._connected = False
        self._connection = None
    
    def is_available(self) -> bool:
        """Check if RCON library is available."""
        return MCRCON_AVAILABLE
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test RCON connection to Minecraft.
        
        Returns:
            Tuple of (success, message)
        """
        if not MCRCON_AVAILABLE:
            return False, "mcrcon library not installed"
        
        try:
            with MCRcon(self.host, self.password, self.port, timeout=self.timeout) as mcr:
                response = mcr.command("say BBS Agent connected!")
                return True, f"Connected successfully. Response: {response}"
        except socket.timeout:
            return False, f"Connection timeout to {self.host}:{self.port}"
        except ConnectionRefusedError:
            return False, f"Connection refused - is RCON enabled in server.properties?"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def execute(self, command: str) -> CommandResult:
        """
        Execute a single command via RCON.
        
        Args:
            command: Minecraft command (without leading /)
            
        Returns:
            CommandResult with success status and response
        """
        if not MCRCON_AVAILABLE:
            return CommandResult(False, "RCON not available", command=command)
        
        # Skip comment-only commands
        if command.startswith('#'):
            return CommandResult(True, "Skipped (comment)", command=command)
        
        try:
            with MCRcon(self.host, self.password, self.port, timeout=self.timeout) as mcr:
                response = mcr.command(command)
                return CommandResult(True, response, command=command)
        except Exception as e:
            return CommandResult(False, str(e), command=command)
    
    def execute_sequence(
        self, 
        commands: List[dict],
        tick_delay_ms: int = 50,
        realtime: bool = True
    ) -> List[CommandResult]:
        """
        Execute a sequence of timed commands.
        
        Args:
            commands: List of command dicts with 'tick' and 'command' keys
            tick_delay_ms: Milliseconds per tick (50ms = 20 TPS)
            realtime: If True, wait between commands based on tick timing
            
        Returns:
            List of CommandResults
        """
        if not MCRCON_AVAILABLE:
            return [CommandResult(False, "RCON not available")]
        
        results = []
        sorted_cmds = sorted(commands, key=lambda x: x.get('tick', 0))
        last_tick = 0
        
        try:
            with MCRcon(self.host, self.password, self.port, timeout=self.timeout) as mcr:
                for cmd_data in sorted_cmds:
                    tick = cmd_data.get('tick', 0)
                    command = cmd_data.get('command', '')
                    
                    # Wait for tick timing if realtime
                    if realtime and tick > last_tick:
                        wait_time = (tick - last_tick) * tick_delay_ms / 1000.0
                        time.sleep(wait_time)
                    
                    # Skip comments
                    if command.startswith('#'):
                        results.append(CommandResult(True, "Skipped", tick, command))
                        continue
                    
                    try:
                        response = mcr.command(command)
                        results.append(CommandResult(True, response, tick, command))
                    except Exception as e:
                        results.append(CommandResult(False, str(e), tick, command))
                    
                    last_tick = tick
                    
        except Exception as e:
            results.append(CommandResult(False, f"Connection error: {e}"))
        
        return results
    
    def setup_world(self, gamemode: str = "creative", difficulty: str = "peaceful") -> List[CommandResult]:
        """
        Set up world for recording.
        
        Args:
            gamemode: Game mode (creative, spectator, survival)
            difficulty: Difficulty level
            
        Returns:
            List of results
        """
        commands = [
            {"tick": 0, "command": f"gamemode {gamemode}"},
            {"tick": 1, "command": f"difficulty {difficulty}"},
            {"tick": 2, "command": "gamerule doDaylightCycle false"},
            {"tick": 3, "command": "gamerule doWeatherCycle false"},
            {"tick": 4, "command": "gamerule doMobSpawning false"},
        ]
        return self.execute_sequence(commands, realtime=False)


class CommandFileExecutor:
    """
    Alternative executor that saves commands to file for manual execution.
    Use when RCON is not available.
    """
    
    def __init__(self, output_dir: str):
        """
        Initialize file executor.
        
        Args:
            output_dir: Directory to save command files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_commands(self, commands: List[dict], filename: str = "commands.txt") -> str:
        """
        Save commands to a file for manual execution.
        
        Args:
            commands: List of command dicts
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write("# BBS AI Agent - Generated Commands\n")
            f.write("# Copy-paste these into Minecraft chat or use a command block\n\n")
            
            sorted_cmds = sorted(commands, key=lambda x: x.get('tick', 0))
            current_tick = -1
            
            for cmd_data in sorted_cmds:
                tick = cmd_data.get('tick', 0)
                command = cmd_data.get('command', '')
                desc = cmd_data.get('description', '')
                
                if tick != current_tick:
                    f.write(f"\n# === Tick {tick} ===\n")
                    current_tick = tick
                
                if desc:
                    f.write(f"# {desc}\n")
                f.write(f"{command}\n")
        
        return filepath
    
    def save_as_datapack(self, commands: List[dict], pack_name: str = "bbs_agent") -> str:
        """
        Save commands as a Minecraft datapack.
        
        Args:
            commands: List of command dicts  
            pack_name: Datapack name
            
        Returns:
            Path to datapack folder
        """
        import json
        
        pack_dir = os.path.join(self.output_dir, pack_name)
        func_dir = os.path.join(pack_dir, "data", pack_name, "functions")
        os.makedirs(func_dir, exist_ok=True)
        
        # pack.mcmeta
        mcmeta = {
            "pack": {
                "pack_format": 15,  # 1.20+
                "description": "BBS AI Agent Generated Animation"
            }
        }
        with open(os.path.join(pack_dir, "pack.mcmeta"), 'w') as f:
            json.dump(mcmeta, f, indent=2)
        
        # Main function
        main_lines = ["# BBS AI Agent - Main Animation Controller", ""]
        
        sorted_cmds = sorted(commands, key=lambda x: x.get('tick', 0))
        for cmd_data in sorted_cmds:
            command = cmd_data.get('command', '')
            if not command.startswith('#'):
                main_lines.append(command)
        
        with open(os.path.join(func_dir, "main.mcfunction"), 'w') as f:
            f.write('\n'.join(main_lines))
        
        return pack_dir


# RCON Setup Guide
RCON_SETUP_GUIDE = """
=== RCON Setup Guide for Minecraft ===

To enable RCON for command execution:

1. For SINGLE-PLAYER with LAN:
   - Open your world
   - Press Esc → "Open to LAN"
   - Enable cheats
   - Note: LAN doesn't support RCON directly

2. For SERVER (recommended):
   Edit server.properties:
   ```
   enable-rcon=true
   rcon.port=25575
   rcon.password=your_password_here
   ```
   Then restart the server.

3. Alternative - Use datapacks:
   The agent can generate datapack files that you
   can manually add to your world's datapacks folder.
   Run with: /reload then /function bbs_agent:main

For this project, we recommend Option 3 (datapacks)
for single-player use, as it doesn't require RCON setup.
"""


# Test
if __name__ == "__main__":
    print("Testing RCON client...")
    
    rcon = MinecraftRCON()
    print(f"RCON available: {rcon.is_available()}")
    
    success, msg = rcon.test_connection()
    print(f"Connection test: {success} - {msg}")
    
    if not success:
        print("\n" + RCON_SETUP_GUIDE)
        
        # Create file-based fallback
        print("\nUsing file-based fallback...")
        executor = CommandFileExecutor("output")
        
        test_commands = [
            {"tick": 0, "command": "gamemode creative", "description": "Set creative mode"},
            {"tick": 10, "command": "time set day", "description": "Set time"},
            {"tick": 20, "command": 'summon armor_stand 0 64 0 {CustomName:\'"test"\'}', "description": "Spawn test actor"},
        ]
        
        filepath = executor.save_commands(test_commands)
        print(f"Commands saved to: {filepath}")
