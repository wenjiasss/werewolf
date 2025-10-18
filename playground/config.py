import random

RETRIES = 3
NAMES = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]  
RUN_SYNTHETIC_VOTES = True
MAX_DEBATE_TURNS = 2  # Reduced from 8 to 2 for lighter CPU load
NUM_PLAYERS = 8

def get_player_names(): 
    return random.sample(NAMES, NUM_PLAYERS)