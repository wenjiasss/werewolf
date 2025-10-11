import datetime
import json
import os
from typing import List, Tuple
from playground.model import RoundLog, State, to_dict

def log_directory():
    pacific_timezone = datetime.timezone(datetime.timedelta(hours=-8))
    timestamp = datetime.datetime.now(pacific_timezone).strftime("%Y%m%d_%H%M%S")
    session_id = f"session_{timestamp}"
    directory = f"{os.getcwd()}/logs/{session_id}"
    return directory

def load_game(directory):
    """Load a game from a file and convert its data to game objects.

    Args:
      directory: where the game log is stored

    Returns:
      State: An instance of the State class populated with the game data.
    """

    partial_game_state_file = f"{directory}/game_partial.json"
    complete_game_state_file = f"{directory}/game_complete.json"
    log_file = f"{directory}/game_logs.json"

    game_state_file = partial_game_state_file
    if not os.path.exists(partial_game_state_file):
        game_state_file = complete_game_state_file

    with open(game_state_file, "r") as file:
        partial_game_data = json.load(file)

    state = State.from_json(partial_game_data)

    with open(log_file, "r") as file:
        logs = json.load(file)

    logs = [RoundLog.from_json(log) for log in logs]

    return (state, logs)


def save_game(state, logs, directory):
    """Save the current game state to a specified file.

    This function serializes the game state to JSON and writes it to the
    specified file. If an error message is provided, it adds the error
    message to the current round of the game state before saving.

    Args:
      state: Instance of the `State` class.
      logs: Logs of the  game.
      directory: where to save the game.
    """
    os.makedirs(directory, exist_ok=True)

    partial_game_state_file = f"{directory}/game_partial.json"
    if state.error_message:
        game_file = partial_game_state_file
    else:
        game_file = f"{directory}/game_complete.json"
        # Remove the partial game file if it exists
        if os.path.exists(partial_game_state_file):
            os.remove(partial_game_state_file)

    log_file = f"{directory}/game_logs.json"

    with open(game_file, "w") as file:
        json.dump(state.to_dict(), file, indent=4)

    with open(log_file, "w") as file:
        json.dump(to_dict(logs), file, indent=4)
