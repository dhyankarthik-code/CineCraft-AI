"""
Video Recorder for BBS AI Agent

Controls video recording via:
1. BBS built-in FFmpeg integration
2. Direct FFmpeg screen capture
3. Minema mod integration
"""

import os
import subprocess
import time
import json
from typing import Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class RecordingSettings:
    """Video recording configuration."""
    width: int = 1920
    height: int = 1080
    fps: int = 60
    codec: str = "libx264"
    quality: int = 18  # CRF value (lower = better)
    format: str = "mp4"


class VideoRecorder:
    """
    Manages video recording for Minecraft animations.
    
    Supports multiple recording methods based on available tools.
    """
    
    def __init__(
        self,
        output_dir: str = None,
        ffmpeg_path: str = None,
        settings: RecordingSettings = None
    ):
        """
        Initialize video recorder.
        
        Args:
            output_dir: Directory for output videos
            ffmpeg_path: Path to FFmpeg executable
            settings: Recording settings
        """
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "..", "output", "videos"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Try to find FFmpeg
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self.settings = settings or RecordingSettings()
        
        # Recording state
        self._recording = False
        self._process = None
    
    def _find_ffmpeg(self) -> Optional[str]:
        """
        Find FFmpeg executable.
        
        Checks:
        1. FFMPEG_PATH environment variable
        2. Minecraft folder (common location)
        3. System PATH
        """
        # Check env var
        env_path = os.getenv("FFMPEG_PATH")
        if env_path:
            ffmpeg_exe = os.path.join(env_path, "ffmpeg.exe") if os.path.isdir(env_path) else env_path
            if os.path.exists(ffmpeg_exe):
                return ffmpeg_exe
        
        # Check Minecraft folder
        mc_dir = os.getenv("MINECRAFT_DIR", os.path.join(os.getenv("APPDATA", ""), ".minecraft"))
        mc_ffmpeg_dirs = [
            os.path.join(mc_dir, "ffmpeg-8.0.1"),
            os.path.join(mc_dir, "ffmpeg"),
        ]
        for ffdir in mc_ffmpeg_dirs:
            ffmpeg_exe = os.path.join(ffdir, "bin", "ffmpeg.exe")
            if os.path.exists(ffmpeg_exe):
                return ffmpeg_exe
            # Some installs have ffmpeg.exe directly in folder
            ffmpeg_exe = os.path.join(ffdir, "ffmpeg.exe")
            if os.path.exists(ffmpeg_exe):
                return ffmpeg_exe
        
        # Check system PATH
        try:
            result = subprocess.run(
                ["where", "ffmpeg"], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def is_available(self) -> Tuple[bool, str]:
        """
        Check if FFmpeg is available.
        
        Returns:
            Tuple of (available, message)
        """
        if not self.ffmpeg_path:
            return False, "FFmpeg not found. Install FFmpeg or set FFMPEG_PATH."
        
        if not os.path.exists(self.ffmpeg_path):
            return False, f"FFmpeg not found at: {self.ffmpeg_path}"
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                return True, f"FFmpeg available: {version}"
        except Exception as e:
            return False, f"FFmpeg error: {e}"
        
        return False, "FFmpeg check failed"
    
    def generate_bbs_recording_config(self) -> dict:
        """
        Generate BBS-compatible recording configuration.
        
        This config can be merged with bbs.json to set up recording.
        """
        return {
            "video": {
                "settings": {
                    "width": self.settings.width,
                    "height": self.settings.height,
                    "frameRate": self.settings.fps,
                    "heldFrames": 1,
                    "motionBlur": 0,
                    "audio": False,
                    "exportPath": self.output_dir,
                    "arguments": f"-f rawvideo -pix_fmt bgr24 -s %WIDTH%x%HEIGHT% -r %FPS% -i - -vf %FILTERS% -c:v {self.settings.codec} -preset ultrafast -tune zerolatency -qp {self.settings.quality} -pix_fmt yuv420p %NAME%.{self.settings.format}"
                },
                "log": True,
                "encoder_path": self.ffmpeg_path or "ffmpeg"
            }
        }
    
    def update_bbs_config(self, bbs_config_path: str) -> bool:
        """
        Update BBS config file with recording settings.
        
        Args:
            bbs_config_path: Path to bbs.json
            
        Returns:
            True if successful
        """
        try:
            # Read existing config
            with open(bbs_config_path, 'r') as f:
                config = json.load(f)
            
            # Update video settings
            recording_config = self.generate_bbs_recording_config()
            config.update(recording_config)
            
            # Write back
            with open(bbs_config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error updating BBS config: {e}")
            return False
    
    def get_output_path(self, name: str) -> str:
        """Generate output file path."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.{self.settings.format}"
        return os.path.join(self.output_dir, filename)
    
    def create_recording_instructions(self, scene_name: str, duration_seconds: int) -> str:
        """
        Generate instructions for manual recording via BBS.
        
        Args:
            scene_name: Name of the scene to record
            duration_seconds: Expected duration
            
        Returns:
            Instruction text
        """
        output_path = self.get_output_path(scene_name)
        
        instructions = f"""
=== BBS Recording Instructions ===

Scene: {scene_name}
Duration: {duration_seconds} seconds
Output: {output_path}

STEPS:
1. Open Minecraft with BBS mod loaded
2. Load your scene/film in BBS editor
3. Press the BBS menu key (default: 0)
4. Go to "Film" → Select your film
5. Click the camera icon (📷) to open recording panel
6. Set these settings:
   - Width: {self.settings.width}
   - Height: {self.settings.height}
   - FPS: {self.settings.fps}
   - Export Path: {self.output_dir}
7. Click "Record" to start recording
8. BBS will play the scene and record to video
9. Video will be saved to: {output_path}

ALTERNATIVE - Manual FFmpeg:
If BBS recording doesn't work, use OBS or:
{self.ffmpeg_path or 'ffmpeg'} -f gdigrab -framerate {self.settings.fps} -i title="Minecraft" -c:v {self.settings.codec} -preset fast -crf {self.settings.quality} "{output_path}"
"""
        return instructions
    
    def start_screen_capture(self, output_name: str, duration: int = None) -> Tuple[bool, str]:
        """
        Start screen capture recording using FFmpeg GDI grab.
        
        Args:
            output_name: Name for output file
            duration: Recording duration in seconds (None = manual stop)
            
        Returns:
            Tuple of (success, message or path)
        """
        if not self.ffmpeg_path:
            return False, "FFmpeg not available"
        
        if self._recording:
            return False, "Already recording"
        
        output_path = self.get_output_path(output_name)
        
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite
            "-f", "gdigrab",  # Windows screen capture
            "-framerate", str(self.settings.fps),
            "-i", "title=Minecraft",  # Capture Minecraft window
            "-c:v", self.settings.codec,
            "-preset", "fast",
            "-crf", str(self.settings.quality),
            "-pix_fmt", "yuv420p",
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
        
        cmd.append(output_path)
        
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self._recording = True
            return True, output_path
        except Exception as e:
            return False, f"Failed to start recording: {e}"
    
    def stop_recording(self) -> Tuple[bool, str]:
        """
        Stop current recording.
        
        Returns:
            Tuple of (success, message)
        """
        if not self._recording or not self._process:
            return False, "Not recording"
        
        try:
            # Send q to FFmpeg to stop gracefully
            self._process.terminate()
            self._process.wait(timeout=10)
            self._recording = False
            return True, "Recording stopped"
        except Exception as e:
            self._process.kill()
            self._recording = False
            return False, f"Error stopping: {e}"
    
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording


class RecordingOrchestrator:
    """
    Orchestrates the complete recording workflow.
    Coordinates scene playback with video recording.
    """
    
    def __init__(self, recorder: VideoRecorder, rcon_client=None):
        """
        Initialize orchestrator.
        
        Args:
            recorder: VideoRecorder instance
            rcon_client: Optional RCON client for command execution
        """
        self.recorder = recorder
        self.rcon = rcon_client
    
    def generate_recording_plan(self, script: dict) -> dict:
        """
        Generate a recording plan from a command script.
        
        Args:
            script: Generated script from BBSCommandGenerator
            
        Returns:
            Recording plan with scenes and timing
        """
        plan = {
            "title": script.get("title", "Untitled"),
            "total_duration_seconds": script.get("total_duration_seconds", 0),
            "output_dir": self.recorder.output_dir,
            "settings": {
                "width": self.recorder.settings.width,
                "height": self.recorder.settings.height,
                "fps": self.recorder.settings.fps
            },
            "scenes": []
        }
        
        for scene in script.get("scenes", []):
            scene_plan = {
                "name": scene["name"],
                "start_tick": scene["start_tick"],
                "duration_ticks": scene["duration_ticks"],
                "duration_seconds": scene["duration_ticks"] / 20,
                "output_file": self.recorder.get_output_path(scene["name"]),
                "command_count": len(scene["commands"])
            }
            plan["scenes"].append(scene_plan)
        
        return plan
    
    def get_workflow_instructions(self, plan: dict) -> str:
        """
        Generate step-by-step workflow instructions.
        
        Args:
            plan: Recording plan from generate_recording_plan
            
        Returns:
            Formatted instruction text
        """
        lines = [
            "=" * 50,
            "BBS AI AGENT - RECORDING WORKFLOW",
            "=" * 50,
            "",
            f"Project: {plan['title']}",
            f"Total Duration: {plan['total_duration_seconds']:.1f} seconds",
            f"Resolution: {plan['settings']['width']}x{plan['settings']['height']} @ {plan['settings']['fps']}fps",
            f"Output Directory: {plan['output_dir']}",
            "",
            "SCENES:",
            "-" * 30,
        ]
        
        for i, scene in enumerate(plan['scenes'], 1):
            lines.extend([
                f"\n{i}. {scene['name']}",
                f"   Duration: {scene['duration_seconds']:.1f}s ({scene['duration_ticks']} ticks)",
                f"   Commands: {scene['command_count']}",
                f"   Output: {scene['output_file']}"
            ])
        
        lines.extend([
            "",
            "=" * 50,
            "WORKFLOW STEPS:",
            "=" * 50,
            "",
            "1. PREPARATION",
            "   - Open Minecraft with BBS mod",
            "   - Load your world",
            "   - Open BBS menu (default key: 0)",
            "",
            "2. LOAD COMMANDS",
            "   - Copy generated commands to command blocks, OR",
            "   - Use /reload if using datapack, OR",
            "   - Execute via RCON if enabled",
            "",
            "3. RECORD EACH SCENE",
            "   - Use BBS recording feature, OR",
            "   - Use screen capture (OBS/FFmpeg)",
            "   - Follow timing for each scene",
            "",
            "4. POST-PROCESSING (Optional)",
            "   - Combine scene videos",
            "   - Add music/effects",
            "   - Export final video",
        ])
        
        return "\n".join(lines)


# Test
if __name__ == "__main__":
    print("Testing Video Recorder...")
    
    recorder = VideoRecorder()
    available, msg = recorder.is_available()
    print(f"FFmpeg: {available} - {msg}")
    
    if available:
        print(f"FFmpeg path: {recorder.ffmpeg_path}")
        
        # Generate BBS config
        config = recorder.generate_bbs_recording_config()
        print("\nBBS Recording Config:")
        print(json.dumps(config, indent=2))
    
    # Generate instructions
    instructions = recorder.create_recording_instructions("test_scene", 30)
    print(instructions)
