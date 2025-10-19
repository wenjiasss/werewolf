import datetime
import json
import os
from model.model import RoundLog, State, to_dict

# Creates a timestamped directory path for saving game logs
def log_directory():
    pacific_timezone = datetime.timezone(datetime.timedelta(hours=-8))
    timestamp = datetime.datetime.now(pacific_timezone).strftime("%Y-%m-%d_%H-%M-%S")
    session_id = f"session_{timestamp}"
    directory = f"{os.getcwd()}/output_metrics/logs/{session_id}"
    return directory

# Load a game from saved JSON files
def load_game(directory):
    # Try to load partial game first (for incomplete games), fallback to complete
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


# Save the current game state to JSON files
def save_game(state, logs, directory):
    os.makedirs(directory, exist_ok=True)

    partial_game_state_file = f"{directory}/game_partial.json"
    if state.error_message:
        game_file = partial_game_state_file
    else:
        game_file = f"{directory}/game_complete.json"
        # Clean up partial file if game completed successfully
        if os.path.exists(partial_game_state_file):
            os.remove(partial_game_state_file)

    log_file = f"{directory}/game_logs.json"

    with open(game_file, "w") as file:
        json.dump(state.to_dict(), file, indent=4)

    with open(log_file, "w") as file:
        json.dump(to_dict(logs), file, indent=4)
