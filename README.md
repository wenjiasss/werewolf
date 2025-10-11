# Agent Beats - Werewolf Game with AI Players

This is an AI-powered implementation of the social deduction game Werewolf (also known as Mafia), where all players are controlled by language models running locally via Ollama.

## Setup

### 1. Install and Start Ollama

Make sure you have [Ollama](https://ollama.ai) installed and running.

Pull a model (recommended for M1 Mac):

```bash
# Recommended: Fast and works well on M1
ollama pull llama3.2:3b

# Alternative options:
ollama pull qwen2.5:3b      # Good balance of speed and quality
ollama pull phi3:mini       # Very fast, smaller
ollama pull gemma2:2b       # Google's efficient model
ollama pull mistral:7b      # Larger, more capable (slower)
```

### 2. Activate the Virtual Environment

```bash
source agent-beats/bin/activate
```

### 3. Install Dependencies

The dependencies should already be installed in your `agent-beats` virtual environment, but if you need to reinstall:

```bash
pip install -r requirements.txt
```

## Running the Game

### Quick Start

Run a single game with Llama 3.2 (default):

```bash
python run_game.py
```

### Advanced Usage

You can use the runner directly with custom flags:

```bash
# Run a single game with Llama 3.2
python -m playground.runner --run=True --v_models=llama3 --w_models=llama3

# Run with Qwen 2.5
python -m playground.runner --run=True --v_models=qwen --w_models=qwen

# Run multiple games for evaluation (2 games)
python -m playground.runner --eval=True --num_games=2 --v_models=llama3 --w_models=llama3

# Run with single thread (slower but more stable)
python -m playground.runner --run=True --v_models=llama3 --w_models=llama3 --threads=1

# Mix models (villagers use Llama, werewolves use Qwen)
python -m playground.runner --run=True --v_models=llama3 --w_models=qwen
```

## Game Output

The game provides **full text output** showing:

1. **Player Assignments**: See which players get which roles (Villager, Werewolf, Seer, Doctor)
2. **Night Phase Actions**: 
   - Werewolves eliminating players
   - Seer investigating players
   - Doctor protecting players
3. **Day Phase Debate**: 
   - Players bidding to speak
   - Full debate dialogue
   - Voting results
4. **Game Results**: Winner and final statistics

### Log Files

After each game, detailed logs are saved to `logs/session_TIMESTAMP/`:
- `game_complete.json`: Complete game state
- `game_logs.json`: Detailed logs of all actions and LM responses

## Available Models

Currently configured models in `playground/runner.py`:

### Ollama Models (Local - Recommended)
- `llama3`: Llama 3.2 3B - Fast and efficient on M1 Mac ⭐ **Recommended**
- `qwen`: Qwen 2.5 3B - Good balance of speed and quality
- `phi`: Phi 3 Mini - Very fast, smaller model
- `gemma`: Gemma 2 2B - Google's efficient model
- `mistral`: Mistral 7B - Larger, more capable (slower)

### Cloud Models (Require API setup)
- `pro1.5`: Gemini 1.5 Pro
- `flash`: Gemini 1.5 Flash
- `gpt4`: GPT-4 Turbo
- `gpt4o`: GPT-4o
- `gpt3.5`: GPT-3.5 Turbo

**Note**: The code is now configured to use Ollama for local inference. No API keys needed!

## Configuration

- **Number of players**: Edit `NUM_PLAYERS` in `playground/config.py` (default: 8)
- **Max debate turns**: Edit `MAX_DEBATE_TURNS` in `playground/config.py` (default: 8)
- **Player names**: Edit `NAMES` list in `playground/config.py`

## Game Rules

- **Player Roles**: 8 players total - 2 Werewolves, 1 Seer, 1 Doctor, 4 Villagers
- **Rounds**: Two phases per round
  - **Night Phase**: Werewolves eliminate, Seer investigates, Doctor protects
  - **Day Phase**: Players debate and vote to exile someone
- **Winning Conditions**: 
  - Villagers win by voting out both Werewolves
  - Werewolves win when they outnumber the Villagers

## Troubleshooting

### Ollama Connection Error

If you get connection errors, make sure Ollama is running:

```bash
# Check if Ollama is running
curl http://localhost:11434

# If not running, start Ollama app or run:
ollama serve
```

### Model Not Found

If you get a model not found error, pull the model first:

```bash
ollama pull llama3.2:3b
```

### Import Errors

Make sure you're running commands from the project root and your virtual environment is activated.

### Module Not Found

If you get module import errors, try:

```bash
export PYTHONPATH=/Users/nitya/Downloads/test_agent_beats:$PYTHONPATH
```

### Performance Tips for M1 Mac

- Use 3B models for best speed/quality balance
- Start with `--threads=1` if you experience issues
- Close other heavy applications for best performance

## Project Structure

```
test_agent_beats/
├── playground/
│   ├── __init__.py          # Package initialization
│   ├── apis.py              # OpenRouter API integration
│   ├── config.py            # Game configuration
│   ├── game.py              # GameMaster and game logic
│   ├── game_logging.py      # Save/load game state
│   ├── lm.py                # Language model utilities
│   ├── model.py             # Player classes and game state
│   ├── prompts.py           # Game prompts for LM
│   ├── runner.py            # Main game runner
│   ├── secret.txt           # API key (not in git)
│   └── utils.py             # Utility functions
├── agent-beats/             # Virtual environment
├── requirements.txt         # Python dependencies
├── run_game.py             # Simple game runner script
└── README.md               # This file
```

