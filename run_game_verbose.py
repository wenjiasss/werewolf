#!/usr/bin/env python3
"""
Run the game with verbose output that bypasses tqdm for better visibility.
"""

import sys
import os

# Ensure unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)

from absl import app

# Import runner first to register flags
from playground import runner

sys.argv = ['run_game.py', '--run=True', '--v_models=llama3', '--w_models=llama3', '--threads=1']

def main(argv):
    print("=" * 60)
    print("🐺 WEREWOLF GAME STARTING")
    print("=" * 60)
    print(f"Model: llama3:8b")
    print(f"Max debate turns: 2 players per round")
    print(f"Press Ctrl+C anytime to stop and save progress")
    print("=" * 60)
    print()
    sys.stdout.flush()
    
    runner.run()

if __name__ == '__main__':
    app.run(main)

