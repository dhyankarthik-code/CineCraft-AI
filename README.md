# 🎬 BBS AI Agent - Minecraft Animation Studio

AI-powered automation for **Blockbuster Studio (BBS)** mod in Minecraft. Create epic machinimas from natural language descriptions!

![Minecraft Animation](https://img.shields.io/badge/Minecraft-1.21-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## ✨ Features

- **Natural Language Input**: Describe your animation story and AI converts it to BBS commands
- **ChatGPT-like Interface**: Easy-to-use Gradio chat UI
- **Multiple Export Options**: Datapack, mcfunction files, or direct RCON execution
- **Video Recording Integration**: FFmpeg support for capturing animations

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Minecraft 1.21 with Blockbuster Studio (BBS) mod
- OpenAI API key

### 2. Installation

```bash
# Clone or navigate to project
# Clone or navigate to project
cd CineCraft-AI

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies (already done if you followed setup)
pip install -r requirements.txt

# Set up environment
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Run the App

```bash
python run.py
```

Open `http://localhost:7860` in your browser.

## 📖 Usage

### Basic Workflow

1. **Enter your story** in the chat:
   ```
   A peaceful village is attacked by titans. The villagers fight back heroically.
   ```

2. **AI generates storyboard** with scenes, actors, cameras, and timing

3. **Generate commands** by typing `generate`

4. **Export files** by typing `export`

5. **Use in Minecraft**:
   - Copy datapack to `world/datapacks/`
   - Run `/reload` then `/function bbs_agent:main`

### Commands

| Command | Description |
|---------|-------------|
| `summary` | Show current storyboard |
| `generate` | Generate BBS commands |
| `export` | Export to datapack files |
| `record` | Get recording instructions |
| `refine [changes]` | Modify the storyboard |
| `reset` | Start a new project |

## 🎥 Recording Your Animation

1. Open Minecraft with BBS mod
2. Load the datapack
3. Use BBS recording feature, or
4. Use OBS/FFmpeg for screen capture

## 📁 Project Structure

```
Mine craft Project/
├── src/
│   ├── agent.py          # Main orchestrator
│   ├── openai_parser.py  # AI script parsing
│   ├── bbs_commands.py   # Command generation
│   ├── rcon_client.py    # Minecraft connection
│   └── video_recorder.py # Recording control
├── ui/
│   └── gradio_app.py     # Chat interface
├── output/               # Generated files
├── reference/            # BBS config samples
├── run.py               # Entry point
├── requirements.txt
└── .env.example
```

## 🔧 Configuration

Edit `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
MINECRAFT_DIR=C:\Users\YourUser\AppData\Roaming\.minecraft
RCON_HOST=localhost
RCON_PORT=25575
RCON_PASSWORD=your_password
```

## 🤝 Contributing

We welcome contributions to CineCraft AI! Here's how you can help:

1.  **Fork the Project**: Create your own copy of the repository.
2.  **Create a Branch**: `git checkout -b feature/AmazingFeature`
3.  **Commit Changes**: `git commit -m 'Add some AmazingFeature'`
4.  **Push to Branch**: `git push origin feature/AmazingFeature`
5.  **Open a Pull Request**: Submit your changes for review.

> [!IMPORTANT]
> For major changes, please open an issue first to discuss what you would like to change. This ensures your work aligns with the project's direction.

## 🎬 Inspired By

This project is designed to create animations in the style of [ZMDE](https://www.youtube.com/watch?v=HllSAOQ03EY) - epic Minecraft narratives featuring:
- Time-lapse civilizations
- Attack on Titan themed transformations
- Large-scale battles
- Cinematic camera work

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

Copyright (c) 2026 Dhyaneshwaran K

---

Made with ❤️ for the Minecraft machinima community
