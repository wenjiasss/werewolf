from runners.runner import run_game

# For FAST DEBUGGING use smaller models:
# - "llama3.2:1b" = 1B params, ~4x faster than 8B
# - "llama3.2:3b" = 3B params, ~2.5x faster than 8B
# - "qwen2.5:1.5b" = 1.5B params, very fast
# For production quality, use: "llama3:8b"

MODEL = "llama3.2:3b"  # FAST DEBUGGING MODE
print("Starting Werewolf...")
print(f"Using {MODEL}\n")
winner, log_dir = run_game(werewolf_model=MODEL, villager_model=MODEL, num_threads=4)

print(f"\n{'='*60}")
print(f"Game complete. Winner: {winner}")
print(f"{'='*60}")
print(f"Logs saved to: {log_dir}")
