# Game Analysis & Metrics Guide

## Overview

The game now includes powerful analysis features to help you understand player reasoning and build suspicion scorecards. Perfect for developing green agents for werewolf tasks!

## New Features

### 1. **Reduced CPU Load** 🎯
- Debate turns reduced from 8 to 2 (configurable in `playground/config.py`)
- Only 2 players speak per round instead of 8
- Significantly faster game completion

### 2. **Auto-Save Game State** 💾
- Game state is saved automatically after each round
- You can press **Ctrl+C** to stop the game at any time
- All progress is preserved, even partial games
- Logs are saved incrementally so you don't lose data

### 3. **Analysis Metrics File** 📊
- Automatically generated after each game
- Located at: `logs/session_TIMESTAMP/analysis_metrics.json`
- Contains comprehensive player reasoning and suspicion data

## Analysis Metrics File Structure

The `analysis_metrics.json` file contains:

### Game Info
```json
{
  "game_info": {
    "session_id": "10",
    "winner": "Villagers" or "Werewolves",
    "total_rounds": 3,
    "players": {
      "Alice": "Villager",
      "Bob": "Werewolf",
      ...
    }
  }
}
```

### Suspicion Scorecard

For EACH player, the following metrics are tracked:

#### **mentioned_players** 
Count of how many times this player mentioned each other player
```json
"mentioned_players": {
  "Bob": 3,    // Mentioned Bob 3 times across all debates
  "Charlie": 1
}
```

#### **suspicious_of**
Count of times this player expressed suspicion toward each player
```json
"suspicious_of": {
  "Bob": 2,    // Expressed suspicion of Bob 2 times
  "David": 1
}
```

#### **trusts**
Count of times this player expressed trust toward each player
```json
"trusts": {
  "Charlie": 1  // Expressed trust in Charlie
}
```

#### **voted_for**
Complete voting history with reasoning
```json
"voted_for": [
  {
    "round": 0,
    "voted_for": "Bob",
    "reasoning": "Bob has been unusually quiet and deflecting questions..."
  }
]
```

#### **debate_contributions**
Everything they said in debates with their reasoning
```json
"debate_contributions": [
  {
    "round": 0,
    "reasoning": "I need to voice my concerns about Bob's behavior...",
    "said": "I think Bob is acting suspicious because..."
  }
]
```

#### **reasoning_history**
Complete round-by-round breakdown of ALL actions with reasoning
```json
"reasoning_history": [
  {
    "round": 0,
    "actions": {
      "bid": {
        "reasoning": "I have critical information to share...",
        "bid": "3"
      },
      "debate": {
        "reasoning": "Need to expose inconsistencies...",
        "say": "Bob claimed he trusted Charlie but..."
      },
      "vote": {
        "target": "Bob",
        "reasoning": "Based on Bob's contradictory statements..."
      },
      "summary": {
        "reasoning": "This round revealed important information...",
        "summary": "I observed that Bob and David seem coordinated..."
      }
    }
  }
]
```

#### **observations**
Private knowledge this player has (what they saw, learned, etc.)
```json
"observations": [
  "Round 0: During the night, I chose to protect Harold",
  "Round 0: Summary: Bob was very defensive when questioned..."
]
```

## Using the Analysis for Green Agents

### Building a Suspicion Scorecard

The analysis file gives you everything you need to understand how each player evaluates others:

1. **Direct Suspicion Signals**
   - Look at `suspicious_of` to see who they think is a werewolf
   - Check `trusts` to see who they believe is innocent
   - Review `mentioned_players` to see who they're focused on

2. **Reasoning Patterns**
   - Examine `reasoning_history` to understand their thought process
   - Look for logical consistency across rounds
   - Identify what information influences their decisions

3. **Behavioral Analysis**
   - Compare what they say vs. how they vote
   - Track how their suspicions evolve over time
   - See if they coordinate with other players

4. **Role-Specific Insights**
   - Werewolves might avoid mentioning each other
   - Seers might subtly guide discussion based on investigations
   - Doctors might protect players they trust

### Example: Building a Suspicion Matrix

You can process the analysis file to build a matrix like:

```
          Bob    Charlie  David
Alice     0.8    0.2      0.5
Bob       0.1    0.3      0.7
Charlie   0.6    0.0      0.4
```

Where each value represents "how suspicious Player A is of Player B"

Calculate by:
- `suspicion_score = suspicious_of[player] / (mentioned_players[player] + 1)`
- Higher score = more suspicious

## Configuration

### Adjust CPU Load

Edit `playground/config.py`:

```python
MAX_DEBATE_TURNS = 2  # Number of people who speak per round
NUM_PLAYERS = 8       # Total players (keep at 8 for balance)
```

For even lighter load:
- `MAX_DEBATE_TURNS = 1` - only 1 player speaks per round
- Use `--threads=1` flag to process sequentially

### Run with Custom Settings

```bash
# Super light mode (1 speaker, 1 thread)
python -m playground.runner --run=True --v_models=llama3 --w_models=llama3 --threads=1

# Default mode (2 speakers, 2 threads)
python run_game.py
```

## Example Analysis Workflow

1. **Run a game** (can interrupt anytime with Ctrl+C):
   ```bash
   python run_game.py
   ```

2. **Find the analysis file**:
   ```bash
   ls logs/session_*/analysis_metrics.json
   ```

3. **Load and analyze**:
   ```python
   import json
   
   with open('logs/session_TIMESTAMP/analysis_metrics.json') as f:
       data = json.load(f)
   
   # Get suspicion scorecard for a specific player
   alice_data = data['suspicion_scorecard']['Alice']
   
   # See who Alice is suspicious of
   print(alice_data['suspicious_of'])
   
   # Read Alice's reasoning for voting
   for vote in alice_data['voted_for']:
       print(f"Round {vote['round']}: Voted for {vote['voted_for']}")
       print(f"Reason: {vote['reasoning']}\n")
   
   # Build suspicion matrix
   for player_name, player_data in data['suspicion_scorecard'].items():
       print(f"\n{player_name} is suspicious of:")
       for suspect, count in player_data['suspicious_of'].items():
           print(f"  - {suspect}: {count} times")
   ```

4. **Train your green agent**:
   - Use the reasoning patterns to understand effective strategies
   - Identify what signals humans/AIs use to detect werewolves
   - Build a model that mimics successful player reasoning

## Tips for Green Agent Development

1. **Pattern Recognition**: Look for common reasoning patterns across multiple games
2. **Consistency Analysis**: Track how consistent players are in their suspicions
3. **Information Usage**: See how players use public vs private information
4. **Social Dynamics**: Analyze how players influence each other's opinions
5. **Deception Detection**: Compare werewolf reasoning vs villager reasoning

## File Locations

After each game, find these files in `logs/session_TIMESTAMP/`:
- `game_complete.json` or `game_partial.json` - Full game state
- `game_logs.json` - Raw LM logs with all API responses
- `analysis_metrics.json` - ⭐ **Your analysis goldmine!**

Happy analyzing! 🐺🎮📊

