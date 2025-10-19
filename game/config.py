import random

# Number of times to retry failed LLM calls before giving up
RETRIES = 2

# Pool of player names (famous werewolves according to Wikipedia)
NAMES = ["Derek", "Scott", "Jacob", "Isaac", "Hayley", "David", "Tyler",
        "Ginger", "Jackson", "Mason", "Dan", "Bert", "Will", "Sam",
        "Paul", "Leah", "Harold"]

# Whether to collect votes after every debate turn (for metrics) or just at the end
RUN_SYNTHETIC_VOTES = True

# Number of debate turns per round
MAX_DEBATE_TURNS = 4

# Total players in the game (2 Werewolves, 1 Seer, 1 Doctor, rest Villagers)
NUM_PLAYERS = 7

# Returns a random sample of player names
def get_player_names(): 
    return random.sample(NAMES, NUM_PLAYERS)
