# Werewolf Agent Game

A multi-agent Werewolf (Mafia) game implementation with role assessments and detailed analytics.

## Project Structure

```
test_agent_beats/
├── analyzers/              # Game analysis and metrics
│   ├── analysis.py         # Core analysis functions
│   └── analyze_multiple_games.py  # Multi-game statistics
├── game/                   # Core game logic
│   ├── config.py           # Game configuration
│   ├── game.py             # Game master and mechanics
│   └── game_logging.py     # Logging and save/load
├── model/                  # AI models and prompts
│   ├── lm.py               # Language model interface
│   ├── model.py            # Player models and game state
│   └── prompts.py          # Game prompts
├── runners/                # Game execution scripts
│   ├── runner.py           # Core runner logic
│   ├── run_game.py         # Single game execution
│   └── run_multiple_games.py  # Multiple game execution
├── output_metrics/         # Game results and logs
│   └── logs/               # Session logs
├── apis.py                 # API wrapper for Ollama
├── utils.py                # Utility functions
└── requirements.txt        # Python dependencies
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install and start Ollama (for local LLM inference):
```bash
# macOS
brew install ollama
ollama serve

# Pull the recommended model
ollama pull llama3.2:3b
```

## Usage

### Run a Single Game
```bash
python runners/run_game.py
```

### Run Multiple Games (for analysis)
```bash
python runners/run_multiple_games.py [num_games]
```

### Analyze Game Results
```bash
# Analyze the 3 most recent games
python analyzers/analyze_multiple_games.py --recent 3

# Analyze specific game sessions
python analyzers/analyze_multiple_games.py output_metrics/logs/session_1 output_metrics/logs/session_2
```

## Output

Game results are saved to `output_metrics/`:
- **logs/session_YYYYMMDD_HHMMSS/** - Individual game sessions with detailed metrics
- **games_summary.csv** - Summary of all analyzed games
- **win_rates.csv** - Win rate statistics by team
- **survival_rates.csv** - Survival rates by role and round
- **survival_by_role_round.csv** - Detailed survival data for plotting

## Features

- **Role-based gameplay**: Werewolves, Villagers, Seer, and Doctor
- **Real-time role assessments**: Players assess each other's roles after every debate turn
- **Comprehensive analytics**: Track belief evolution, influence, consistency, and more
- **Local LLM support**: Uses Ollama for privacy and offline capability
- **Resume functionality**: Games auto-save and can be resumed after interruption

## Configuration

Edit `game/config.py` to adjust:
- Number of players
- Number of debate turns per round
- Player names
- Retry attempts for LLM calls

