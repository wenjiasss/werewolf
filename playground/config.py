import random

RETRIES = 3
NAMES = ["Derek", "Scott", "Jacob", "Isaac", "Hayley", "David", "Tyler",
        "Ginger", "Jackson", "Mason", "Dan", "Bert", "Will", "Sam",
        "Paul", "Leah", "Harold"]  # famous werewolves according to Wikipedia
RUN_SYNTHETIC_VOTES = True
MAX_DEBATE_TURNS = 2  # Reduced from 8 to 2 for lighter CPU load
NUM_PLAYERS = 8

def get_player_names(): 
    return random.sample(NAMES, NUM_PLAYERS)