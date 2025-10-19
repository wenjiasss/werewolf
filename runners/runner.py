import random
import traceback
import itertools
import pandas as pd
import os
import datetime
from absl import flags
import tqdm
import uuid
from game import game_logging as logging
from game import game
from model.model import Doctor
from model.model import SEER
from model.model import Seer
from model.model import State
from model.model import Villager
from model.model import WEREWOLF
from model.model import Werewolf
from game.config import get_player_names
from analyzers import analysis

_RUN_GAME = flags.DEFINE_boolean("run", False, "Runs a single game.")
_RESUME = flags.DEFINE_boolean("resume", False, "Resumes games.")
_EVAL = flags.DEFINE_boolean("eval", False, "Collect eval data by running many games.")
_NUM_GAMES = flags.DEFINE_integer(
    "num_games", 2, "Number of games to run used with eval."
)
_VILLAGER_MODELS = flags.DEFINE_list(
    "v_models", "", "The model used for villagers values are: flash, pro, gpt4"
)
_WEREWOLF_MODELS = flags.DEFINE_list(
    "w_models", "", "The model used for werewolves values are: flash, pro, gpt4"
)
_ARENA = flags.DEFINE_boolean(
    "arena", False, "Only run games using different models for villagers and werewolves"
)
_THREADS = flags.DEFINE_integer("threads", 2, "Number of threads to run.")
DEFAULT_WEREWOLF_MODELS = ["gemma", "llama3"]
DEFAULT_VILLAGER_MODELS = ["gemma", "llama3"]
RESUME_DIRECTORIES = []

model_to_id = {
    "llama3-8b": "llama3:8b",           
    "qwen": "qwen3:8b",         
}

# Assigns roles to players and initializes their game view
def initialize_players(villager_model, werewolf_model):

    player_names = get_player_names()
    random.shuffle(player_names)

    seer = Seer(name=player_names.pop(), model=villager_model, personality="You are cunning.") # always one seer
    doctor = Doctor(name=player_names.pop(), model=villager_model, personality="You are a doctor.") # always one doctor
    werewolves = [Werewolf(name=player_names.pop(), model=werewolf_model) for _ in range(2)] # always two werewolves
    villagers = [Villager(name=name, model=villager_model) for name in player_names] # remaining players are villagers

    # Initialize game view for all players
    for player in [seer, doctor] + werewolves + villagers:
        other_wolf = ( 
            next((w.name for w in werewolves if w != player), None)
            if isinstance(player, Werewolf)
            else None
        )
        tqdm.tqdm.write(f"{player.name} has role {player.role}")
        player.initialize_game_view(
            current_players=player_names
            + [seer.name, doctor.name]
            + [w.name for w in werewolves],
            round_number=0,
            other_wolf=other_wolf,
        )
    return seer, doctor, villagers, werewolves


def resume_game(directory: str):
    state, logs = logging.load_game(directory)

    # remove the failed round and resume from the beginning of that round.
    last_round = state.rounds[-1]
    if not last_round.success:
        state.rounds.pop()
        logs.pop()
    # Reset the error state
    state.error_message = ""

    if not state.rounds:
        werewolves = []
        for p in state.players.values():
            p.initialize_game_view(round_number=0, current_players=list(state.players.keys()))
            p.observations = []

            if p.role == WEREWOLF:
                werewolves.append(p)

            if p.role == SEER:
                p.previously_unmasked = {}

        if len(werewolves) == 2:
            werewolves[0].gamestate.other_wolf = werewolves[1].name
            werewolves[1].gamestate.other_wolf = werewolves[0].name
    else:
        # Update the GameView for every active player
        werewolves = []
        for p in state.rounds[-1].players:
            player = state.players.get(p, None)
            if player:
                player.initialize_game_view(round_number=len(state.rounds), current_players=state.rounds[-1].players[:])

                # Remove the observation from the failed round for all active players
                failed_round = len(state.rounds)
                player.observations = [o for o in player.observations if not o.startswith(f"Round {failed_round}")]

                if player.role == WEREWOLF:
                    werewolves.append(player)

                # Update the seer's unmasking history
                unmasking_history = {}
                if player.role == SEER:
                    for r in state.rounds:
                        if r.unmasked:
                            unmasked_player = state.players.get(r.unmasked, None)
                            if unmasked_player:
                                unmasking_history[r.unmasked] = unmasked_player.role
                    player.previously_unmasked = unmasking_history

        if len(werewolves) == 2:
            werewolves[0].gamestate.other_wolf = werewolves[1].name
            werewolves[1].gamestate.other_wolf = werewolves[0].name

    gm = game.GameMaster(state, num_threads=_THREADS.value)
    gm.logs = logs

    try:
        gm.run_game()
    except Exception as e:
        state.error_message = traceback.format_exc()
    logging.save_game(state, gm.logs, directory)
    return not state.error_message


def resume_games(directories):
    successful_resumes = []
    failed_resumes = []
    invalid_resumes = []
    for i in tqdm.tqdm(range(len(directories)), desc="Games"):
        d = directories[i]

        try:
            success = resume_game(d)
            if success:
                successful_resumes.append(d)
            else:
                failed_resumes.append(d)
        except Exception as e:
            if "not found" in str(e):
                invalid_resumes.append(d)
            print(f"Error encountered during resume: {e}")

    print(f"Successful resumes: {successful_resumes}.\nFailed resumes:"
        f" {failed_resumes}\nInvalid resumes(no partial game found):"
        f" {invalid_resumes}"
    )


def run_game(werewolf_model, villager_model, num_threads=2):    
    seer, doctor, villagers, werewolves = initialize_players(villager_model, werewolf_model)
    session_id = str(uuid.uuid4())
    state = State(villagers=villagers, werewolves=werewolves, seer=seer, doctor=doctor, session_id=session_id)
    
    # Create log directory upfront
    log_directory = logging.log_directory()
    
    # Pass log_directory to GameMaster for auto-saving
    gamemaster = game.GameMaster(state, num_threads=num_threads, log_directory=log_directory)
    winner = None

    try:
        # Save initial state
        logging.save_game(state, gamemaster.logs, log_directory)
        print(f"Game started. Logs auto-saving to: {log_directory}")
        winner = gamemaster.run_game()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Saving current state...")
        state.error_message = "Game interrupted"
    except Exception as e:
        state.error_message = traceback.format_exc()
        print(f"Error encountered during game: {e}")
    finally:
        # Always save game state (even if interrupted)
        logging.save_game(state, gamemaster.logs, log_directory)
        print(f"Game logs saved to: {log_directory}")
        
        # Generate analysis metrics
        try:
            analysis.save_analysis(state, gamemaster.logs, log_directory)
        except Exception as e:
            print(f"Could not generate analysis: {e}")
    
    return winner, log_directory


def run():
    villager_models = _VILLAGER_MODELS.value or DEFAULT_VILLAGER_MODELS
    werewolf_models = _WEREWOLF_MODELS.value or DEFAULT_WEREWOLF_MODELS
    v_ids = [model_to_id[m] for m in villager_models]
    w_ids = [model_to_id[m] for m in werewolf_models]
    model_combinations = list(itertools.product(v_ids, w_ids))

    if _RUN_GAME.value:
        villager_model, werewolf_model = model_combinations[0]
        print(f"Villagers: {villager_model} versus Werwolves:  {werewolf_model}")
        run_game(werewolf_model=werewolf_model, villager_model=villager_model, num_threads=_THREADS.value)
        
    elif _EVAL.value:
        results = []
        for villager_model, werewolf_model in model_combinations:
            # Only run games using different models in the arena mode
            if villager_model == werewolf_model and _ARENA.value:
                continue
            print(
                f"Running games with Villagers: {villager_model} and"
                f" Werewolves:{werewolf_model}"
            )
            for _ in tqdm.tqdm(range(_NUM_GAMES.value), desc="Games"):
                winner, log_dir = run_game(
                    werewolf_model=werewolf_model,
                    villager_model=villager_model,
                    num_threads=_THREADS.value,
                )
                results.append([villager_model, werewolf_model, winner, log_dir])

        df = pd.DataFrame(
            results, columns=["VillagerModel", "WerewolfModel", "Winner", "Log"]
        )
        print("######## Eval results ########")
        print(df)

        pacific_timezone = datetime.timezone(datetime.timedelta(hours=-8))
        timestamp = datetime.datetime.now(pacific_timezone).strftime("%Y%m%d_%H%M%S")
        csv_file = f"{os.getcwd()}/output_metrics/eval_results_{timestamp}.csv"
        df.to_csv(csv_file)
        print(f"Wrote eval results to {csv_file}")

    elif _RESUME.value:
        resume_games(RESUME_DIRECTORIES)