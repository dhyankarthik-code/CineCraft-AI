"""
BBS AI Agent - Main Orchestrator

The central agent that coordinates all components:
- Script parsing via OpenAI
- Command generation for BBS
- Execution via RCON or file export
- Video recording workflow

Designed for ZMDE-style epic Minecraft machinimas.
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Local imports
from .openai_parser import ScriptParser
from .bbs_commands import BBSCommandGenerator
from .rcon_client import MinecraftRCON, CommandFileExecutor
from .video_recorder import VideoRecorder, RecordingOrchestrator, RecordingSettings

load_dotenv()


@dataclass
class AgentState:
    """Tracks the current state of the agent."""
    current_storyboard: Optional[dict] = None
    current_script: Optional[dict] = None
    current_recording_plan: Optional[dict] = None
    last_error: Optional[str] = None
    execution_log: List[dict] = field(default_factory=list)
    
    def log(self, action: str, details: str = "", success: bool = True):
        self.execution_log.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "details": details,
            "success": success
        })


class BBSAgent:
    """
    AI-powered automation agent for Blockbuster Studio.
    
    Workflow:
    1. User inputs natural language script
    2. AI parses script into structured storyboard
    3. Storyboard converts to BBS commands
    4. Commands execute via RCON or export as files
    5. Recording captures the animation as video
    
    Example:
        agent = BBSAgent()
        agent.process_script("A village is attacked by titans...")
        agent.generate_commands()
        agent.export_to_files()  # or agent.execute_via_rcon()
    """
    
    def __init__(
        self,
        openai_api_key: str = None,
        openai_model: str = "gpt-4o",
        minecraft_dir: str = None,
        output_dir: str = None
    ):
        """
        Initialize the BBS AI Agent.
        
        Args:
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            openai_model: Model to use for script parsing
            minecraft_dir: Path to .minecraft folder
            output_dir: Directory for output files
        """
        self.minecraft_dir = minecraft_dir or os.getenv(
            "MINECRAFT_DIR", 
            os.path.join(os.getenv("APPDATA", ""), ".minecraft")
        )
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "..", "output"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize components
        self.parser = ScriptParser(api_key=openai_api_key, model=openai_model)
        self.command_gen = BBSCommandGenerator()
        self.rcon = MinecraftRCON()
        self.file_executor = CommandFileExecutor(os.path.join(self.output_dir, "commands"))
        self.recorder = VideoRecorder(output_dir=os.path.join(self.output_dir, "videos"))
        self.orchestrator = RecordingOrchestrator(self.recorder, self.rcon)
        
        # Agent state
        self.state = AgentState()
        
        # Check system status
        self._check_system_status()
    
    def _check_system_status(self) -> Dict[str, Any]:
        """Check status of all components."""
        status = {
            "openai": True,  # Will fail on first use if invalid
            "rcon": self.rcon.is_available(),
            "ffmpeg": self.recorder.is_available(),
            "minecraft_dir": os.path.exists(self.minecraft_dir),
            "bbs_installed": os.path.exists(
                os.path.join(self.minecraft_dir, "config", "bbs")
            )
        }
        
        self.system_status = status
        return status
    
    def get_status_report(self) -> str:
        """Generate human-readable status report."""
        status = self._check_system_status()
        
        lines = [
            "=" * 50,
            "BBS AI AGENT - SYSTEM STATUS",
            "=" * 50,
            "",
        ]
        
        for component, available in status.items():
            icon = "✅" if available else "❌"
            lines.append(f"{icon} {component.replace('_', ' ').title()}")
        
        # Additional details
        lines.extend([
            "",
            f"Minecraft Dir: {self.minecraft_dir}",
            f"Output Dir: {self.output_dir}",
            "",
        ])
        
        if not status["rcon"]:
            lines.append("⚠️  RCON not available - will use file export mode")
        
        ffmpeg_ok, ffmpeg_msg = self.recorder.is_available()
        if ffmpeg_ok:
            lines.append(f"📹 {ffmpeg_msg}")
        else:
            lines.append(f"⚠️  {ffmpeg_msg}")
        
        return "\n".join(lines)
    
    def process_script(self, script: str, custom_instructions: str = None) -> dict:
        """
        Process a natural language script into a storyboard.
        
        Args:
            script: The story/animation description
            custom_instructions: Additional requirements
            
        Returns:
            Storyboard dictionary
        """
        self.state.log("process_script", f"Processing {len(script)} characters")
        
        try:
            storyboard = self.parser.parse_script(script, custom_instructions)
            self.state.current_storyboard = storyboard
            self.state.log("process_script", f"Generated {len(storyboard.get('scenes', []))} scenes", True)
            return storyboard
        except Exception as e:
            self.state.last_error = str(e)
            self.state.log("process_script", str(e), False)
            raise
    
    def refine_storyboard(self, refinement: str) -> dict:
        """
        Refine the current storyboard.
        
        Args:
            refinement: What to change or add
            
        Returns:
            Updated storyboard
        """
        if not self.state.current_storyboard:
            raise ValueError("No storyboard to refine. Call process_script first.")
        
        self.state.log("refine_storyboard", refinement[:100])
        storyboard = self.parser.refine_storyboard(refinement)
        self.state.current_storyboard = storyboard
        return storyboard
    
    def get_storyboard_summary(self) -> str:
        """Get human-readable summary of current storyboard."""
        if not self.state.current_storyboard:
            return "No storyboard generated yet."
        return self.parser.get_scene_summary(self.state.current_storyboard)
    
    def generate_commands(self) -> dict:
        """
        Generate BBS commands from current storyboard.
        
        Returns:
            Command script dictionary
        """
        if not self.state.current_storyboard:
            raise ValueError("No storyboard available. Call process_script first.")
        
        self.state.log("generate_commands", "Generating BBS commands")
        
        script = self.command_gen.generate_full_script(self.state.current_storyboard)
        self.state.current_script = script
        
        total_cmds = sum(len(s["commands"]) for s in script.get("scenes", []))
        self.state.log("generate_commands", f"Generated {total_cmds} commands", True)
        
        return script
    
    def export_to_files(self) -> Dict[str, str]:
        """
        Export commands to files for manual execution.
        
        Returns:
            Dictionary of {file_type: file_path}
        """
        if not self.state.current_script:
            raise ValueError("No commands generated. Call generate_commands first.")
        
        self.state.log("export_to_files", "Exporting to files")
        
        # Collect all commands
        all_commands = []
        for scene in self.state.current_script.get("scenes", []):
            all_commands.extend(scene["commands"])
        
        # Export as text file
        txt_path = self.file_executor.save_commands(
            all_commands, 
            f"{self.state.current_script.get('title', 'animation').replace(' ', '_')}.txt"
        )
        
        # Export as datapack
        pack_path = self.file_executor.save_as_datapack(
            all_commands,
            "bbs_agent"
        )
        
        # Export as mcfunction files
        func_dir = os.path.join(self.output_dir, "mcfunctions")
        func_files = self.command_gen.export_to_mcfunction(
            self.state.current_script, 
            func_dir
        )
        
        result = {
            "commands_txt": txt_path,
            "datapack": pack_path,
            "mcfunctions": func_dir
        }
        
        self.state.log("export_to_files", f"Exported to {len(result)} locations", True)
        return result
    
    def execute_via_rcon(self, realtime: bool = False) -> List[dict]:
        """
        Execute commands via RCON if available.
        
        Args:
            realtime: If True, wait between commands based on tick timing
            
        Returns:
            List of execution results
        """
        if not self.rcon.is_available():
            raise RuntimeError("RCON not available. Use export_to_files instead.")
        
        if not self.state.current_script:
            raise ValueError("No commands generated. Call generate_commands first.")
        
        self.state.log("execute_via_rcon", f"Executing (realtime={realtime})")
        
        # Collect all commands
        all_commands = []
        for scene in self.state.current_script.get("scenes", []):
            all_commands.extend(scene["commands"])
        
        results = self.rcon.execute_sequence(all_commands, realtime=realtime)
        
        success_count = sum(1 for r in results if r.success)
        self.state.log(
            "execute_via_rcon", 
            f"{success_count}/{len(results)} commands succeeded",
            success_count == len(results)
        )
        
        return [{"success": r.success, "response": r.response, "command": r.command} for r in results]
    
    def get_recording_plan(self) -> dict:
        """
        Generate recording plan for the current animation.
        
        Returns:
            Recording plan dictionary
        """
        if not self.state.current_script:
            raise ValueError("No commands generated. Call generate_commands first.")
        
        plan = self.orchestrator.generate_recording_plan(self.state.current_script)
        self.state.current_recording_plan = plan
        return plan
    
    def get_recording_instructions(self) -> str:
        """
        Get step-by-step recording instructions.
        
        Returns:
            Formatted instruction text
        """
        if not self.state.current_recording_plan:
            self.get_recording_plan()
        
        return self.orchestrator.get_workflow_instructions(self.state.current_recording_plan)
    
    def save_project(self, filename: str = None) -> str:
        """
        Save the current project state to JSON.
        
        Args:
            filename: Output filename (optional)
            
        Returns:
            Path to saved file
        """
        if not filename:
            title = "untitled"
            if self.state.current_storyboard:
                title = self.state.current_storyboard.get("title", "untitled")
            filename = f"{title.replace(' ', '_')}_project.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        project = {
            "storyboard": self.state.current_storyboard,
            "script": self.state.current_script,
            "recording_plan": self.state.current_recording_plan,
            "execution_log": self.state.execution_log,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(filepath, 'w') as f:
            json.dump(project, f, indent=2)
        
        self.state.log("save_project", filepath)
        return filepath
    
    def load_project(self, filepath: str) -> bool:
        """
        Load a saved project.
        
        Args:
            filepath: Path to project JSON
            
        Returns:
            True if successful
        """
        try:
            with open(filepath, 'r') as f:
                project = json.load(f)
            
            self.state.current_storyboard = project.get("storyboard")
            self.state.current_script = project.get("script")
            self.state.current_recording_plan = project.get("recording_plan")
            
            self.state.log("load_project", filepath)
            return True
        except Exception as e:
            self.state.last_error = str(e)
            self.state.log("load_project", str(e), False)
            return False
    
    def reset(self):
        """Reset agent state for a new project."""
        self.state = AgentState()
        self.parser.reset_conversation()
        self.state.log("reset", "Agent state reset")


def create_agent(**kwargs) -> BBSAgent:
    """Factory function to create a BBSAgent with default settings."""
    return BBSAgent(**kwargs)


# Quick test
if __name__ == "__main__":
    print("BBS AI Agent - Quick Test")
    print("=" * 50)
    
    agent = BBSAgent()
    print(agent.get_status_report())
    
    print("\nTo use the agent:")
    print("  agent = BBSAgent()")
    print('  agent.process_script("Your story here...")')
    print("  agent.generate_commands()")
    print("  agent.export_to_files()")
