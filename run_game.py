#!/usr/bin/env python3
"""
Simple script to run a Werewolf game with Qwen model.

Usage:
    python run_game.py
"""

import sys
from absl import app

# Import runner first to register flags
from playground import runner

sys.argv = ['run_game.py', '--run=True', '--v_models=llama3', '--w_models=llama3']

def main(argv):
    runner.run()

if __name__ == '__main__':
    app.run(main)

