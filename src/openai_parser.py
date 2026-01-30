"""
OpenAI Script Parser for BBS AI Agent

Converts natural language scripts into structured storyboard JSON
for Blockbuster Studio animation automation.

Designed for ZMDE-style epic Minecraft narratives:
- Time-lapse civilizations (1000 years)
- Attack on Titan themed transformations
- Villager populations vs monsters
- Epic battles and dramatic camera work
"""

import os
import json
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ZMDE-style system prompt for storyboard generation
STORYBOARD_SYSTEM_PROMPT = """You are a professional Minecraft machinima director specializing in epic, 
cinematic animations like ZMDE's "Titan Garden VS Villagers For 1000 Years".

Your job is to convert natural language story scripts into structured storyboard JSON that can be 
used to automate Blockbuster Studio (BBS) mod in Minecraft.

OUTPUT FORMAT (JSON):
{
    "title": "Video title",
    "total_duration_seconds": 240,
    "scenes": [
        {
            "id": "scene_001",
            "name": "Scene Name",
            "description": "What happens in this scene",
            "duration_seconds": 30,
            "time_period": "Year 1 - The Beginning",
            "setting": {
                "location": "Village center",
                "time_of_day": "day",
                "weather": "clear",
                "world_modifications": ["Build wooden houses", "Plant crops around village"]
            },
            "actors": [
                {
                    "id": "actor_001",
                    "name": "farmer_1",
                    "type": "villager",
                    "skin": "villager_farmer",
                    "spawn_position": [100, 64, 100],
                    "actions": [
                        {
                            "tick": 0,
                            "type": "spawn",
                            "position": [100, 64, 100]
                        },
                        {
                            "tick": 20,
                            "type": "walk_to",
                            "target_position": [110, 64, 100],
                            "speed": 1.0
                        },
                        {
                            "tick": 100,
                            "type": "action",
                            "action_name": "interact",
                            "target": "crops"
                        },
                        {
                            "tick": 200,
                            "type": "morph",
                            "morph_to": "titan_form",
                            "duration_ticks": 40
                        }
                    ]
                }
            ],
            "camera": {
                "type": "cinematic",
                "movements": [
                    {
                        "tick_start": 0,
                        "tick_end": 100,
                        "type": "orbit",
                        "center": [105, 70, 100],
                        "radius": 20,
                        "start_angle": 0,
                        "end_angle": 180,
                        "height": 10
                    },
                    {
                        "tick_start": 100,
                        "tick_end": 200,
                        "type": "dolly",
                        "start_position": [85, 70, 100],
                        "end_position": [125, 70, 100],
                        "look_at": "actor_001"
                    }
                ],
                "fov_keyframes": [
                    {"tick": 0, "fov": 70},
                    {"tick": 180, "fov": 40}
                ]
            },
            "effects": [
                {
                    "tick": 150,
                    "type": "particles",
                    "particle_type": "explosion",
                    "position": [110, 65, 100],
                    "count": 50
                }
            ],
            "audio": {
                "background_music": null,
                "sound_effects": [
                    {"tick": 150, "sound": "entity.generic.explode", "volume": 1.0}
                ]
            }
        }
    ],
    "global_settings": {
        "ticks_per_second": 20,
        "video_resolution": [1920, 1080],
        "chroma_key": false,
        "loop": false
    }
}

ACTION TYPES AVAILABLE:
- spawn: Spawn actor at position (CREATURES ONLY: zombies, cows, dragons, titans). 
  (NOTE: Do NOT use 'spawn' for buildings like Castles, Villages, Houses. Use 'world_modifications' for those).
- walk_to: Walk to target position
- run_to: Run to target position
- teleport: Instant teleport
- action: Perform action (attack, place, break, interact, use, swipe, jump)
- morph: Transform into another form (for Titan transformations)
- emote: Play emote animation
- look_at: Look at position or actor
- equip: Equip item in hand
- mount: Mount entity
- dismount: Dismount entity
- death: Death animation
- idle: Stand still

CAMERA TYPES:
- static: Fixed position camera
- orbit: Orbit around center point
- dolly: Move from A to B
- follow: Follow an actor
- path: Complex bezier path
- shake: Camera shake effect

IMPORTANT GUIDELINES:
1. **CONTINUITY (CRITICAL):**
   - Assume a CONTINUOUS world. If the user mentions "the dragon", "the castle", or "Zoro", assume they ALREADY EXIST.
   - **Do NOT** include a "spawn" action for existing entities. Only include "spawn" if the user explicitly says "create", "spawn", or "brand new".
   - If commanding an existing entity, just list it in 'actors' with its actions (walk, run, etc.) and NO spawn action.

2. **STRUCTURES:** If the user asks for a building (Castle, Village, House, Tower), put it in the "setting" -> "world_modifications" list as key string (e.g., "Castle", "Village"). Do NOT create an actor for it.

3. **CREATURES:** Only use 'actors' for living things (or moving non-living things like robots).
4. Epic scale - think civilizations, not individuals
5. Time-lapse storytelling - show passage of years
6. Dramatic transformations (villager → titan)
7. Large group scenes (armies, populations)
8. Dynamic camera movements (orbits, dramatic reveals)
9. Build-up tension before action sequences
10. Use environmental changes to show time (buildings grow, forests spread)

Always output valid JSON. Be creative with cinematic techniques."""


class ScriptParser:
    """
    Parses natural language scripts into BBS-compatible storyboards.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize the parser with OpenAI credentials.
        
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: OpenAI model to use (default: gpt-4o)
       """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.conversation_history = []
    
    def parse_script(self, script: str, custom_instructions: Optional[str] = None) -> dict:
        """
        Convert a natural language script to a structured storyboard.
        
        Args:
            script: Natural language description of the animation
            custom_instructions: Additional context or requirements
            
        Returns:
            Storyboard dictionary with scenes, actors, cameras, etc.
        """
        user_message = f"Create a detailed storyboard for this Minecraft animation:\n\n{script}"
        
        if custom_instructions:
            user_message += f"\n\nAdditional requirements:\n{custom_instructions}"
        
        # Add to conversation history for iterative refinement
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        messages = [
            {"role": "system", "content": STORYBOARD_SYSTEM_PROMPT},
            *self.conversation_history
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=4096
            )
            
            content = response.choices[0].message.content
            storyboard = json.loads(content)
            
            # Add AI response to history for context
            self.conversation_history.append({
                "role": "assistant",
                "content": content
            })
            
            return storyboard
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")
    
    def refine_storyboard(self, refinement_request: str) -> dict:
        """
        Refine the last generated storyboard based on feedback.
        
        Args:
            refinement_request: What to change or add
            
        Returns:
            Updated storyboard dictionary
        """
        if not self.conversation_history:
            raise ValueError("No storyboard to refine. Call parse_script first.")
        
        return self.parse_script(refinement_request)
    
    def reset_conversation(self):
        """Clear conversation history for a fresh start."""
        self.conversation_history = []
    
    def get_scene_summary(self, storyboard: dict) -> str:
        """
        Generate a human-readable summary of the storyboard.
        
        Args:
            storyboard: The storyboard dictionary
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(f"📽️ {storyboard.get('title', 'Untitled')}")
        lines.append(f"⏱️ Total Duration: {storyboard.get('total_duration_seconds', 0)} seconds")
        lines.append(f"🎬 Scenes: {len(storyboard.get('scenes', []))}")
        lines.append("")
        
        for i, scene in enumerate(storyboard.get('scenes', []), 1):
            lines.append(f"Scene {i}: {scene.get('name', 'Unnamed')}")
            lines.append(f"  📍 {scene.get('setting', {}).get('location', 'Unknown location')}")
            lines.append(f"  ⏰ {scene.get('duration_seconds', 0)}s - {scene.get('time_period', '')}")
            lines.append(f"  👥 Actors: {len(scene.get('actors', []))}")
            lines.append(f"  📷 Camera: {scene.get('camera', {}).get('type', 'static')}")
            lines.append("")
        
        return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    parser = ScriptParser()
    
    test_script = """
    A peaceful Minecraft village. Farmers tend their crops. 
    Suddenly, one villager begins to transform, growing into a massive Titan.
    The other villagers flee in terror as the Titan roars.
    """
    
    print("Parsing script...")
    storyboard = parser.parse_script(test_script)
    print(parser.get_scene_summary(storyboard))
    print("\nFull storyboard:")
    print(json.dumps(storyboard, indent=2))
