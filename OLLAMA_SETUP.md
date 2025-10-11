# Ollama Setup for Agent Beats Werewolf Game

## What Changed

The game has been updated to run **locally on your M1 Mac using Ollama** instead of using OpenRouter's rate-limited free API.

### Benefits of Ollama
✅ **No rate limits** - Run as many games as you want  
✅ **No API costs** - Everything runs locally  
✅ **Faster** - No network latency  
✅ **Private** - Your game data stays on your machine  
✅ **Offline** - Works without internet connection  

## Quick Start

### 1. Make sure Ollama is installed and running

If you haven't installed Ollama yet:
```bash
# Install via Homebrew
brew install ollama

# Or download from https://ollama.ai
```

Start Ollama (if not already running):
```bash
# Option 1: Open the Ollama app from Applications
# Option 2: Run in terminal
ollama serve
```

### 2. Pull a model

```bash
# Recommended for M1 Mac (fast and good quality)
ollama pull llama3.2:3b
```

### 3. Run the game

```bash
python run_game.py
```

That's it! 🎮

## Recommended Models for M1 Mac

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `llama3.2:3b` | ~2GB | ⚡⚡⚡ | ⭐⭐⭐ | **Best overall** - Fast and smart |
| `qwen2.5:3b` | ~2GB | ⚡⚡⚡ | ⭐⭐⭐ | Great alternative |
| `phi3:mini` | ~2GB | ⚡⚡⚡⚡ | ⭐⭐ | Fastest, simpler responses |
| `gemma2:2b` | ~1.5GB | ⚡⚡⚡⚡ | ⭐⭐ | Lightest option |
| `mistral:7b` | ~4GB | ⚡⚡ | ⭐⭐⭐⭐ | Most capable, slower |

## Running the Game

### Basic usage:
```bash
python run_game.py
```

### With different models:
```bash
# Use Qwen instead of Llama
python -m playground.runner --run=True --v_models=qwen --w_models=qwen

# Mix models (villagers use Llama, werewolves use Qwen)
python -m playground.runner --run=True --v_models=llama3 --w_models=qwen

# Use only 1 thread (more stable, slower)
python -m playground.runner --run=True --v_models=llama3 --w_models=llama3 --threads=1
```

### Running multiple games:
```bash
# Run 5 games for evaluation
python -m playground.runner --eval=True --num_games=5 --v_models=llama3 --w_models=llama3
```

## What You'll See

The game outputs full text showing:
- 🎭 Player role assignments (Villager, Werewolf, Seer, Doctor)
- 🌙 Night phase: Werewolves eliminate, Seer investigates, Doctor protects
- ☀️ Day phase: Full debate dialogue between AI players
- 🗳️ Voting and elimination results
- 🏆 Final game outcome

Example output:
```
Mason has role Seer
David has role Doctor
Will has role Werewolf
Dan has role Werewolf
Derek has role Villager
...
STARTING ROUND: 0
The Werewolves are picking someone to remove from the game.
Dan eliminated David
The Doctor is protecting someone.
David protected Tyler
...
```

## Troubleshooting

### "Connection refused" error
**Problem:** Ollama isn't running  
**Solution:** 
```bash
# Start Ollama
ollama serve

# Or open the Ollama app
```

### "Model not found" error
**Problem:** Model hasn't been downloaded  
**Solution:**
```bash
ollama pull llama3.2:3b
```

### Slow performance
**Problem:** Model too large for your system  
**Solution:** Try a smaller model:
```bash
ollama pull phi3:mini
python -m playground.runner --run=True --v_models=phi --w_models=phi
```

### Game crashes or errors
**Problem:** Model generating invalid JSON  
**Solution:** 
- Use `--threads=1` to reduce concurrent requests
- Try a different model (llama3.2:3b is most reliable)

## Performance Tips

1. **Close other apps** - Free up RAM for better performance
2. **Start with 3B models** - Best balance of speed and quality
3. **Use 1 thread** - More stable, especially on first run
4. **Monitor Activity Monitor** - Watch CPU and RAM usage
5. **Try different models** - Some work better for this game than others

## Files Changed

1. **`playground/apis.py`** - Now uses Ollama API instead of OpenRouter
2. **`playground/runner.py`** - Added Ollama model configurations
3. **`run_game.py`** - Default to llama3.2:3b
4. **`README.md`** - Updated with Ollama instructions
5. **`setup_ollama.sh`** - Automated setup script

## Need Help?

1. Check Ollama is running: `curl http://localhost:11434`
2. List installed models: `ollama list`
3. Test a model: `ollama run llama3.2:3b "Hello"`
4. See Ollama logs: Check the Ollama app
