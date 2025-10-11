# 🚀 Quick Start Guide

## What You Have Now

✅ **Fast 3B Model**: `llama3.2:3b` (2GB) - 2-3x faster than 8B!  
✅ **Reduced Debate**: Only 2 speakers per round (was 8)  
✅ **Auto-Save**: Game saves after every round  
✅ **Ctrl+C Safe**: Stop anytime, progress is saved  
✅ **Analysis Metrics**: Automatic suspicion scorecard generation  

## Run the Game

```bash
python run_game.py
```

That's it! The game will:
- Use the fast `llama3.2:3b` model
- Show real-time text output
- Save progress automatically
- Generate analysis when done

## During the Game

- **See**: Player assignments, debates, votes, eliminations in real-time
- **Stop**: Press `Ctrl+C` anytime to stop and save
- **Resume**: Game state is saved in `logs/session_TIMESTAMP/`

## After the Game

Find 3 files in `logs/session_TIMESTAMP/`:

1. **`game_complete.json`** - Full game state
2. **`game_logs.json`** - All LM API calls
3. **`analysis_metrics.json`** - ⭐ Suspicion scorecards!

## Analysis File

The `analysis_metrics.json` contains for EACH player:
- Who they mentioned (counts)
- Who they're suspicious of (counts)  
- Who they trust (counts)
- Complete voting history with reasoning
- All debate contributions with reasoning
- Round-by-round action reasoning

Perfect for training your green agent! 🎯

## Tips

**Too Slow?**
- Use `--threads=1` for sequential processing
- Close other apps to free up RAM

**Want to See More**:
- Check `logs/session_TIMESTAMP/` for full details
- Read `ANALYSIS_GUIDE.md` for using the metrics

**Customize**:
- Edit `playground/config.py` to change:
  - `MAX_DEBATE_TURNS` (default: 2)
  - `NUM_PLAYERS` (default: 8)

## Models Available

- `llama3` → `llama3.2:3b` ⚡ **Default - FAST**
- `llama3-8b` → `llama3:8b` (2-3x slower)
- `qwen` → `qwen3:8b`

Change model:
```bash
python -m playground.runner --run=True --v_models=qwen --w_models=qwen
```
