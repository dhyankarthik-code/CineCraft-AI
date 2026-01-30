# BBS AI Agent - Minecraft Animation Automation
# =============================================
# AI-powered automation for Blockbuster Studio (BBS) mod
# Creates epic ZMDE-style Minecraft machinimas from natural language

# Quick Start:
# 1. Activate venv: .\venv\Scripts\activate
# 2. Set your API key: copy .env.example to .env and add your OpenAI key
# 3. Run the app: python -m ui.gradio_app

"""
BBS AI Agent - Main Entry Point
"""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.gradio_app import main

if __name__ == "__main__":
    main()
