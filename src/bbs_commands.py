"""
BBS Command Generator

Converts storyboard JSON into Minecraft/Blockbuster Studio commands.
Generates sequences for scene setup, actor control, camera movements, and recording.
"""

import json
import math
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class BBSCommand:
    """Represents a single BBS/Minecraft command with timing."""
    tick: int
    command: str
    description: str = ""
    command_type: str = "minecraft"  # minecraft, bbs, scene
    
    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "command": self.command,
            "description": self.description,
            "type": self.command_type
        }


@dataclass  
class CommandSequence:
    """A sequence of commands for a scene or action."""
    name: str
    commands: List[BBSCommand] = field(default_factory=list)
    duration_ticks: int = 0
    
    def add(self, tick: int, command: str, description: str = "", cmd_type: str = "minecraft"):
        self.commands.append(BBSCommand(tick, command, description, cmd_type))
        self.duration_ticks = max(self.duration_ticks, tick)
    
    def to_list(self) -> List[dict]:
        return [cmd.to_dict() for cmd in sorted(self.commands, key=lambda x: x.tick)]


class BBSCommandGenerator:
    """
    Generates Blockbuster Studio commands from storyboard data.
    
    Supports:
    - Actor spawning and control via armor stands or BBS actors
    - Camera path generation
    - Scene setup with director blocks
    - Particle effects and world modifications
    """
    
    # Minecraft ticks per second
    TPS = 20
    
    # BBS action mappings
    ACTION_MAP = {
        "attack": "swipe",
        "place": "place", 
        "break": "break",
        "interact": "interact",
        "use": "use",
        "swipe": "swipe",
        "jump": "jump"
    }
    
    def __init__(self, base_position: Tuple[int, int, int] = (0, 64, 0)):
        """
        Initialize the command generator.
        
        Args:
            base_position: World origin for relative positioning
        """
        self.base_x, self.base_y, self.base_z = base_position
        self.actor_registry = {}  # Track spawned actors
    
    def _parse_pos(self, pos: list) -> list:
        """Ensure position coordinates are floats."""
        new_pos = []
        for x in pos:
            try:
                if isinstance(x, str):
                    val = x.replace("~", "")
                    if val == "": val = "0"
                    new_pos.append(float(val))
                else:
                    new_pos.append(float(x))
            except (ValueError, TypeError):
                new_pos.append(0.0)
        return new_pos
    
    def generate_scene_commands(self, scene: dict) -> CommandSequence:
        """
        Generate all commands for a scene.
        
        Args:
            scene: Scene dictionary from storyboard
            
        Returns:
            CommandSequence with all scene commands
        """
        seq = CommandSequence(name=scene.get('name', 'unnamed_scene'))
        
        # Scene initialization
        seq.add(0, self._time_command(scene), "Set time of day")
        seq.add(0, self._weather_command(scene), "Set weather")
        
        # World modifications (buildings, terrain)
        for i, mod in enumerate(scene.get('setting', {}).get('world_modifications', [])):
            mod_lower = mod.lower()
            cmd = None
            if "castle" in mod_lower:
                # Vanilla structure: pillager_outpost is most castle-like
                cmd = "execute at @p run place structure minecraft:pillager_outpost ~ ~ ~"
            elif "village" in mod_lower:
                cmd = "execute at @p run place structure minecraft:village_plains ~ ~ ~"
            elif "house" in mod_lower:
                # Small house structure
                cmd = "execute at @p run place structure minecraft:plains_village_shepherds_house_1 ~ ~ ~"
            elif "tower" in mod_lower:
                cmd = "execute at @p run place structure minecraft:pillager_outpost ~ ~ ~"
            else:
                cmd = f"say [Agent] World Mod: {mod}"
            
            if cmd:
                seq.add(i * 5, cmd, f"Build {mod}")
        
        # Actor commands
        for actor in scene.get('actors', []):
            actor_cmds = self._generate_actor_commands(actor)
            for cmd in actor_cmds.commands:
                seq.commands.append(cmd)
        
        # Camera setup
        camera_cmds = self._generate_camera_commands(scene.get('camera', {}))
        for cmd in camera_cmds.commands:
            seq.commands.append(cmd)
        
        # Effects
        for effect in scene.get('effects', []):
            effect_cmd = self._generate_effect_command(effect)
            seq.commands.append(effect_cmd)
        
        # Calculate duration
        duration_seconds = scene.get('duration_seconds', 30)
        seq.duration_ticks = duration_seconds * self.TPS
        
        return seq
    
    def _time_command(self, scene: dict) -> str:
        """Generate time-of-day command."""
        time_map = {
            "day": "time set day",
            "noon": "time set noon", 
            "sunset": "time set 12000",
            "night": "time set night",
            "midnight": "time set midnight",
            "sunrise": "time set 23000"
        }
        time_of_day = scene.get('setting', {}).get('time_of_day', 'day')
        return time_map.get(time_of_day, "time set day")
    
    def _weather_command(self, scene: dict) -> str:
        """Generate weather command."""
        weather_map = {
            "clear": "weather clear",
            "rain": "weather rain",
            "thunder": "weather thunder",
            "storm": "weather thunder"
        }
        weather = scene.get('setting', {}).get('weather', 'clear')
        return weather_map.get(weather, "weather clear")
    
    def _generate_actor_commands(self, actor: dict) -> CommandSequence:
        """Generate commands to control an actor."""
        seq = CommandSequence(name=f"actor_{actor.get('id', 'unknown')}")
        actor_name = actor.get('name', 'actor')
        actor_id = actor.get('id', 'actor_001')
        
        for action in actor.get('actions', []):
            tick = action.get('tick', 0)
            action_type = action.get('type', 'idle')
            
            if action_type == 'spawn':
                raw_pos = action.get('position', [0, 64, 0])
                
                # Titan mod entities (from The Titans Mod)
                titan_entities = {
                    "titan": "titans:zombie_titan",
                    "zombie_titan": "titans:zombie_titan",
                    "creeper_titan": "titans:creeper_titan",
                    "skeleton_titan": "titans:skeleton_titan",
                    "spider_titan": "titans:spider_titan",
                    "blaze_titan": "titans:blaze_titan",
                    "ghast_titan": "titans:ghast_titan",
                    "slime_titan": "titans:slime_titan",
                    "ender_colossus": "titans:ender_colossus",
                    "witherzilla": "titans:witherzilla",
                    "ultima_iron_golem": "titans:ultima_iron_golem_titan",
                }
                
                actor_type = actor.get('type', 'unknown').lower().replace(" ", "_")
                clean_name = actor_name.lower().replace(" ", "_")
                
                # Determine Entity ID
                entity_id = None
                
                # 1. Check if 'type' is a known valid entity (priority)
                # If actor_type is 'villager', use it!
                if actor_type != 'unknown' and actor_type != 'actor' and "titan" not in actor_type:
                     entity_id = f"minecraft:{actor_type}"

                # 2. If no valid type from input, try to deduce from name
                if not entity_id:
                    # Check for Titan mod entities
                    if clean_name in titan_entities:
                        entity_id = titan_entities[clean_name]
                    elif "titan" in clean_name:
                         # Smart matching for titans
                        for prefix in ["zombie", "creeper", "skeleton", "spider", "blaze", "ghast", "slime"]:
                            if prefix in clean_name:
                                entity_id = f"titans:{prefix}_titan"
                                break
                        if not entity_id:
                            entity_id = "titans:zombie_titan"
                    elif "dragon" in clean_name:
                        entity_id = "minecraft:ender_dragon"
                    else:
                        # Fallback to name as type (e.g. "pig")
                        entity_id = f"minecraft:{clean_name}"

                # Generate Custom Name NBT
                nbt_data = ""
                # If the name is specific (not just "cow_1"), use it as CustomName
                # Heuristic: If name is different from type, it's likely a custom name
                if actor_name.lower() != actor_type and actor_name.lower() not in entity_id:
                     nbt_data = f'{{CustomName:\'{{"text":"{actor_name}"}}\'}}'

                # Generate keyframe command
                cmd = f'execute at @p run summon {entity_id} ~ ~ ~ {nbt_data}'
                
                # Fix for Ender Dragon AI
                if "ender_dragon" in entity_id:
                    cmd = f'execute at @p run summon {entity_id} ~ ~ ~ {{DragonPhase:0}}'
                
                seq.add(tick, cmd, f"Spawn {actor_name}")
                self.actor_registry[actor_id] = {"name": actor_name, "position": raw_pos, "type": entity_id}
                
            else:
                # For non-spawn actions, we need to target the entity
                # Helper to determine selector
                selector = self._get_target_selector(actor_name, actor.get('type', 'unknown'))
                
                if action_type == 'walk_to' or action_type == 'run_to':
                    target = action.get('target_position', [0, 64, 0])
                    # Use tp for simple movement
                    cmd = f'tp {selector} {target[0]} {target[1]} {target[2]}'
                    seq.add(tick, cmd, f"{actor_name} moves to {target}")
                    
                elif action_type == 'sit':
                    # Data merge to set sitting
                    cmd = f'data merge entity {selector} {{Sitting:1b}}'
                    # For camels/others
                    if "camel" in actor_name.lower():
                        cmd = f'data merge entity {selector} {{Pose:sitting}}'
                    seq.add(tick, cmd, f"{actor_name} sits")
                
                elif action_type == 'teleport':
                    pos = action.get('position', [0, 64, 0])
                    cmd = f'tp {selector} {pos[0]} {pos[1]} {pos[2]}'
                    seq.add(tick, cmd, f"Teleport {actor_name}")
                    
                elif action_type == 'jump':
                    # Vertical jump using Motion
                    cmd = f'execute as {selector} run data merge entity @s {{Motion:[0.0d,0.6d,0.0d]}}'
                    seq.add(tick, cmd, f"{actor_name} jumps")
                    
                elif action_type == 'attack' or action_type == 'swipe':
                    # Play attack sound and slight lunge
                    cmd1 = f'execute at {selector} run playsound entity.player.attack.strong master @a ~ ~ ~ 1 1'
                    cmd2 = f'execute as {selector} run data merge entity @s {{Motion:[0.0d,0.2d,0.4d]}}' # Lunge forward
                    seq.add(tick, cmd1, f"{actor_name} attacks (sound)")
                    seq.add(tick, cmd2, f"{actor_name} attacks (motion)")

                elif action_type == 'interact':
                    cmd = f'execute at {selector} run playsound entity.villager.trade master @a ~ ~ ~ 1 1'
                    seq.add(tick, cmd, f"{actor_name} interacts")

                elif action_type == 'look_at':
                    target = action.get('target', '0 0 0') # ID or position
                    # If target looks like coords
                    if isinstance(target, list) or (isinstance(target, str) and re.match(r'[\d\s\.\-~]+', target)):
                        if isinstance(target, str): target = target.split()
                        cmd = f'execute as {selector} at @s run facing {target[0]} {target[1]} {target[2]}'
                    else:
                        # Assume it's an entity name
                        target_sel = self._get_target_selector(target, 'unknown')
                        cmd = f'execute as {selector} at @s run facing entity {target_sel} eyes'
                    
                    seq.add(tick, cmd, f"{actor_name} looks at {target}")
        
        return seq

    def _get_target_selector(self, name: str, actor_type: str) -> str:
        """Determines the best selector to target an entity."""
        clean_name = name.lower().replace(" ", "_")
        clean_type = actor_type.lower().replace(" ", "_")
        
        # 1. If name is generic (e.g. "cow"), target by type
        # Check against known entities list (reconstructed simply here)
        known_types = ["zombie", "skeleton", "creeper", "cow", "sheep", "pig", "chicken", "dragon", "titan"]
        
        is_generic = clean_name in known_types or clean_name == clean_type
        
        if is_generic or "dragon" in clean_name:
            # Target by type
            entity_type = clean_type if clean_type != "unknown" else clean_name
            if "dragon" in clean_name: entity_type = "minecraft:ender_dragon"
            elif "titan" in clean_name: entity_type = "titans:zombie_titan" # simplistic fallback
            elif ":" not in entity_type: entity_type = f"minecraft:{entity_type}"
            
            return f"@e[type={entity_type},sort=nearest,limit=1]"
        else:
            # Target by custom name
            return f"@e[name=\"{name}\",sort=nearest,limit=1]"

    
    def _generate_camera_commands(self, camera: dict) -> CommandSequence:
        """Generate camera control commands."""
        seq = CommandSequence(name="camera")
        
        # For now, generate spectator mode teleports
        # In full BBS, this would use Aperture camera clips
        
        for movement in camera.get('movements', []):
            tick_start = movement.get('tick_start', 0)
            tick_end = movement.get('tick_end', 100)
            move_type = movement.get('type', 'static')
            
            if move_type == 'static':
                pos = movement.get('position', [0, 70, 0])
                cmd = f'tp @p {pos[0]} {pos[1]} {pos[2]}'
                seq.add(tick_start, cmd, "Static camera position", "camera")
                
            elif move_type == 'orbit':
                center = self._parse_pos(movement.get('center', [0, 64, 0]))
                radius = float(movement.get('radius', 10))
                start_angle = float(movement.get('start_angle', 0))
                end_angle = float(movement.get('end_angle', 360))
                height = float(movement.get('height', 5))
                
                # Generate keyframe positions for orbit
                num_frames = min(20, (tick_end - tick_start) // 5)
                for i in range(num_frames + 1):
                    t = i / num_frames
                    angle = math.radians(start_angle + (end_angle - start_angle) * t)
                    x = center[0] + radius * math.cos(angle)
                    z = center[2] + radius * math.sin(angle)
                    y = center[1] + height
                    
                    # Calculate look direction toward center
                    tick = tick_start + int((tick_end - tick_start) * t)
                    cmd = f'tp @p {x:.1f} {y:.1f} {z:.1f} facing {center[0]} {center[1]} {center[2]}'
                    seq.add(tick, cmd, f"Orbit frame {i}", "camera")
                    
            elif move_type == 'dolly':
                start_pos = self._parse_pos(movement.get('start_position', [0, 70, 0]))
                end_pos = self._parse_pos(movement.get('end_position', [10, 70, 0]))
                look_at = movement.get('look_at', None)
                
                num_frames = min(20, (tick_end - tick_start) // 5)
                for i in range(num_frames + 1):
                    t = i / num_frames
                    x = start_pos[0] + (end_pos[0] - start_pos[0]) * t
                    y = start_pos[1] + (end_pos[1] - start_pos[1]) * t
                    z = start_pos[2] + (end_pos[2] - start_pos[2]) * t
                    
                    tick = tick_start + int((tick_end - tick_start) * t)
                    if look_at and look_at in self.actor_registry:
                        cmd = f'tp @p {x:.1f} {y:.1f} {z:.1f} facing entity @e[name="{self.actor_registry[look_at]["name"]}"]'
                    else:
                        cmd = f'tp @p {x:.1f} {y:.1f} {z:.1f}'
                    seq.add(tick, cmd, f"Dolly frame {i}", "camera")
                    
            elif move_type == 'follow':
                target = movement.get('target', None)
                distance = movement.get('distance', 5)
                height = movement.get('height', 2)
                
                # Follow commands would be generated per-tick in playback
                seq.add(tick_start, 
                       f"# Camera follows {target} at distance {distance}", 
                       "Follow camera setup", "camera")
        
        # FOV keyframes (would need Aperture mod)
        for fov_kf in camera.get('fov_keyframes', []):
            tick = fov_kf.get('tick', 0)
            fov = fov_kf.get('fov', 70)
            # Minecraft doesn't have direct FOV command, but Aperture does
            seq.add(tick, f"# Set FOV to {fov}", f"FOV keyframe", "aperture")
        
        return seq
    
    def _generate_effect_command(self, effect: dict) -> BBSCommand:
        """Generate particle/effect command."""
        tick = effect.get('tick', 0)
        effect_type = effect.get('type', 'particles')
        
        if effect_type == 'particles':
            particle = effect.get('particle_type', 'cloud')
            pos = effect.get('position', [0, 64, 0])
            count = effect.get('count', 10)
            
            # Map common names to Minecraft particles
            particle_map = {
                "explosion": "explosion",
                "smoke": "smoke",
                "fire": "flame",
                "magic": "enchant",
                "portal": "portal",
                "heart": "heart",
                "cloud": "cloud",
                "dust": "dust 1 0 0 1",  # Red dust
                "growth": "happy_villager"
            }
            mc_particle = particle_map.get(particle, particle)
            
            cmd = f'particle {mc_particle} {pos[0]} {pos[1]} {pos[2]} 1 1 1 0 {count}'
            return BBSCommand(tick, cmd, f"{particle} effect", "minecraft")
        
        return BBSCommand(tick, "# Unknown effect", "Placeholder", "comment")
    
    def generate_full_script(self, storyboard: dict) -> Dict[str, Any]:
        """
        Generate complete command script for entire storyboard.
        
        Args:
            storyboard: Full storyboard dictionary
            
        Returns:
            Dictionary with scene sequences and metadata
        """
        result = {
            "title": storyboard.get('title', 'Untitled'),
            "total_duration_ticks": 0,
            "scenes": []
        }
        
        current_tick_offset = 0
        
        for scene in storyboard.get('scenes', []):
            scene_seq = self.generate_scene_commands(scene)
            
            # Offset all commands by current position
            for cmd in scene_seq.commands:
                cmd.tick += current_tick_offset
            
            result["scenes"].append({
                "name": scene_seq.name,
                "start_tick": current_tick_offset,
                "duration_ticks": scene_seq.duration_ticks,
                "commands": scene_seq.to_list()
            })
            
            current_tick_offset += scene_seq.duration_ticks
        
        result["total_duration_ticks"] = current_tick_offset
        result["total_duration_seconds"] = current_tick_offset / self.TPS
        
        return result
    
    def export_to_mcfunction(self, script: Dict[str, Any], output_dir: str) -> List[str]:
        """
        Export commands as .mcfunction files for datapack.
        
        Args:
            script: Generated script from generate_full_script
            output_dir: Directory to save mcfunction files
            
        Returns:
            List of created file paths
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        files_created = []
        
        # Main orchestrator function
        main_lines = ["# Auto-generated by BBS AI Agent", ""]
        
        for scene in script.get('scenes', []):
            scene_name = scene['name'].replace(' ', '_').lower()
            filename = f"{scene_name}.mcfunction"
            filepath = os.path.join(output_dir, filename)
            
            lines = [f"# Scene: {scene['name']}", f"# Duration: {scene['duration_ticks']} ticks", ""]
            
            for cmd_data in scene['commands']:
                if cmd_data['type'] != 'comment':
                    lines.append(f"# Tick {cmd_data['tick']}: {cmd_data['description']}")
                    lines.append(cmd_data['command'])
                    lines.append("")
            
            with open(filepath, 'w') as f:
                f.write('\n'.join(lines))
            
            files_created.append(filepath)
            main_lines.append(f"# Scene: {scene['name']} - {scene['duration_ticks']} ticks")
            main_lines.append(f"function bbs_agent:{scene_name}")
            main_lines.append("")
        
        # Write main function
        main_path = os.path.join(output_dir, "main.mcfunction")
        with open(main_path, 'w') as f:
            f.write('\n'.join(main_lines))
        files_created.append(main_path)
        
        return files_created


# Test
if __name__ == "__main__":
    generator = BBSCommandGenerator(base_position=(100, 64, 100))
    
    test_scene = {
        "name": "Titan Awakening",
        "duration_seconds": 30,
        "setting": {
            "time_of_day": "sunset",
            "weather": "clear"
        },
        "actors": [
            {
                "id": "villager_1",
                "name": "farmer",
                "actions": [
                    {"tick": 0, "type": "spawn", "position": [100, 64, 100]},
                    {"tick": 40, "type": "walk_to", "target_position": [110, 64, 100]},
                    {"tick": 100, "type": "morph", "morph_to": "titan"}
                ]
            }
        ],
        "camera": {
            "movements": [
                {
                    "tick_start": 0,
                    "tick_end": 200,
                    "type": "orbit",
                    "center": [105, 64, 100],
                    "radius": 15,
                    "start_angle": 0,
                    "end_angle": 180,
                    "height": 8
                }
            ]
        },
        "effects": [
            {"tick": 100, "type": "particles", "particle_type": "explosion", "position": [110, 65, 100], "count": 30}
        ]
    }
    
    seq = generator.generate_scene_commands(test_scene)
    print(f"Generated {len(seq.commands)} commands for scene '{seq.name}'")
    print("\nCommands:")
    for cmd in sorted(seq.commands, key=lambda x: x.tick)[:10]:
        print(f"  [{cmd.tick:4d}] {cmd.command[:60]}...")
