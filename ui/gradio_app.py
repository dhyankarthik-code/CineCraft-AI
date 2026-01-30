"""
BBS AI Agent - Simple ChatGPT-like Interface
Clean, minimal design focused on conversation
"""

import os
import sys
import json
import gradio as gr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import BBSAgent
from dotenv import load_dotenv

load_dotenv()

# Global agent
agent = None

def get_agent():
    global agent
    if agent is None:
        agent = BBSAgent()
    return agent

def chat(message, history):
    """Simple chat function - returns just the response text."""
    if not message.strip():
        return history, ""
    
    try:
        a = get_agent()
        msg_lower = message.lower().strip()
        
        # Handle commands
        if msg_lower in ["status", "check"]:
            response = a.get_status_report()
        
        elif msg_lower in ["reset", "clear", "new"]:
            a.reset()
            response = "🔄 Reset! Ready for a new animation."
        
        elif msg_lower == "summary":
            response = a.get_storyboard_summary() if a.state.current_storyboard else "No storyboard yet. Tell me your story first!"
        
        elif msg_lower == "generate":
            if not a.state.current_storyboard:
                response = "⚠️ Tell me your story first, then I'll generate commands."
            else:
                script = a.generate_commands()
                total_cmds = sum(len(s["commands"]) for s in script.get("scenes", []))
                response = f"✅ Generated {len(script.get('scenes', []))} scenes with {total_cmds} commands!\n\nType 'export' to save files."
        
        elif msg_lower == "export":
            if not a.state.current_script:
                response = "⚠️ Generate commands first! Type 'generate'."
            else:
                files = a.export_to_files()
                response = f"💾 Exported!\n\n📄 Commands: {files['commands_txt']}\n📦 Datapack: {files['datapack']}\n\nIn Minecraft: /reload then /function bbs_agent:main"
        
        elif msg_lower == "record":
            response = a.get_recording_instructions() if a.state.current_script else "Generate and export first!"
        
        elif msg_lower.startswith("refine "):
            if not a.state.current_storyboard:
                response = "⚠️ No storyboard to refine. Tell me a story first!"
            else:
                a.refine_storyboard(message[7:])
                response = f"✨ Refined!\n\n{a.get_storyboard_summary()}"
        
        elif msg_lower == "help":
            response = """📖 **Commands:**
• Just type your story to create a storyboard
• `generate` - Create Minecraft commands
• `export` - Save files for Minecraft
• `summary` - View current storyboard
• `refine [changes]` - Modify storyboard
• `reset` - Start over"""
        
        else:
            # Treat as story input
            storyboard = a.process_script(message)
            num_scenes = len(storyboard.get('scenes', []))
            response = f"🎬 Created {num_scenes} scene(s)!\n\n{a.get_storyboard_summary()}\n\nType 'generate' to create commands."
    
    except Exception as e:
        response = f"❌ Error: {str(e)}"
    
    history.append([message, response])
    return history, ""

# Simple clean interface
with gr.Blocks(
    title="BBS AI Agent",
    theme=gr.themes.Soft(primary_hue="red"),
    css="""
    .gradio-container { max-width: 900px !important; margin: auto !important; }
    footer { display: none !important; }
    """
) as demo:
    
    gr.Markdown("# 🎬 BBS AI Agent\n*Describe your Minecraft animation and I'll create it*")
    
    chatbot = gr.Chatbot(
        height=500,
        show_label=False,
        container=True
    )
    
    with gr.Row():
        msg = gr.Textbox(
            placeholder="Describe your epic Minecraft story... (or type 'help' for commands)",
            show_label=False,
            scale=6,
            container=False
        )
        send = gr.Button("Send", variant="primary", scale=1)
    
    gr.Markdown("*Try: 'A village is attacked by titans. The villagers fight back and win.'*", elem_classes=["hint"])
    
    # Event handlers
    send.click(chat, [msg, chatbot], [chatbot, msg])
    msg.submit(chat, [msg, chatbot], [chatbot, msg])

if __name__ == "__main__":
    print("🎬 BBS AI Agent - Simple Mode")
    demo.launch(server_name="0.0.0.0", server_port=7860, inbrowser=True)
