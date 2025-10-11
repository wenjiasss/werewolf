from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import List
from playground.model import Round, RoundLog, VoteLog
from playground.config import  MAX_DEBATE_TURNS, RUN_SYNTHETIC_VOTES
import random
import tqdm

# Gets all the keys with the highest value in a dictionary
def get_max_bids(dict):
  max_value = max(dict.values())
  max_keys = [key for key, value in dict.items() if value == max_value]
  return max_keys

class GameMaster:

  def __init__(self, state, num_threads=1, log_directory=None):
    self.state = state
    self.current_round_num = len(self.state.rounds) if self.state.rounds else 0
    self.num_threads = num_threads
    self.logs = [] # list of RoundLog objects
    self.log_directory = log_directory  # For auto-saving

  @property # auto-updates when state.rounds changes
  def this_round(self):
    return self.state.rounds[self.current_round_num]

  @property
  def this_round_log(self): # auto-updates when logs changes
    return self.logs[self.current_round_num]
  
  # Werewolves choose a player to eliminate
  def eliminate(self):
    werewolves_alive = [w for w in self.state.werewolves if w.name in self.this_round.players]
    wolf = random.choice(werewolves_alive)
    eliminated, log = wolf.eliminate()
    self.this_round_log.eliminate = log

    if eliminated is not None:
      self.this_round.eliminated = eliminated
      tqdm.tqdm.write(f"{wolf.name} eliminated {eliminated}")
      for wolf in werewolves_alive:
        wolf._add_observation(
            "During the"
            f" night, {'we' if len(werewolves_alive) > 1 else 'I'} decided to"
            f" eliminate {eliminated}."
        )
    else:
      raise ValueError("Eliminate did not return a valid player.")

  # Doctor chooses a player to protect
  def protect(self):
    if self.state.doctor.name not in self.this_round.players:
      return  # Doctor no longer in the game

    protect, log = self.state.doctor.save()
    self.this_round_log.protect = log

    if protect is not None:
      self.this_round.protected = protect
      tqdm.tqdm.write(f"{self.state.doctor.name} protected {protect}")
    else:
      # If model fails to return valid player, choose randomly as fallback
      import random
      protect = random.choice(self.this_round.players)
      self.this_round.protected = protect
      tqdm.tqdm.write(f"⚠️ Doctor action failed, randomly protecting {protect}")

  # Seer chooses a player to unmask
  def unmask(self):
    if self.state.seer.name not in self.this_round.players:
      return  # Seer no longer in the game

    unmask, log = self.state.seer.unmask()
    self.this_round_log.investigate = log

    if unmask is not None:
      self.this_round.unmasked = unmask
      self.state.seer.reveal_and_update(unmask, self.state.players[unmask].role)
    else:
      # If model fails, choose randomly from uninvestigated players
      import random
      options = [p for p in self.this_round.players 
                if p != self.state.seer.name and p not in self.state.seer.previously_unmasked]
      if options:
        unmask = random.choice(options)
        self.this_round.unmasked = unmask
        self.state.seer.reveal_and_update(unmask, self.state.players[unmask].role)
        tqdm.tqdm.write(f"⚠️ Seer action failed, randomly investigating {unmask}")

  # Gets the bid for a specific player (private function)
  def _get_bid(self, player_name):
    player = self.state.players[player_name]
    bid, log = player.bid()
    if bid is None:
      raise ValueError(
          f"{player_name} did not return a valid bid. Find the raw response"
          " in the bid field in the log"
      )
    if bid > 1:
      tqdm.tqdm.write(f"{player_name} bid: {bid}")
    return bid, log

  # Determine the next speaker based on bids
  def get_next_speaker(self):
    previous_speaker, previous_dialogue = (self.this_round.debate[-1] if self.this_round.debate else (None, None))

    with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
      player_bids = {
          player_name: executor.submit(self._get_bid, player_name)
          for player_name in self.this_round.players
          if player_name != previous_speaker
      }

      bid_log = []
      bids = {}

      try:
        for player_name, bid_task in player_bids.items():
          bid, log = bid_task.result()
          bids[player_name] = bid
          bid_log.append((player_name, log))
      except TypeError as e:
        print(e)
        raise e

    self.this_round.bids.append(bids)
    self.this_round_log.bid.append(bid_log)

    potential_speakers = get_max_bids(bids)
    # Prioritize mentioned speakers if there's previous dialogue
    if previous_dialogue:
      potential_speakers.extend(
          [name for name in potential_speakers if name in previous_dialogue]
      )

    random.shuffle(potential_speakers)
    return random.choice(potential_speakers)

  # Collect summaries from players after the debate
  def run_summaries(self):
    with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
      player_summaries = {
          name: executor.submit(self.state.players[name].summarize)
          for name in self.this_round.players
      }

      for player_name, summary_task in player_summaries.items():
        summary, log = summary_task.result()
        tqdm.tqdm.write(f"{player_name} summary: {summary}")
        self.this_round_log.summaries.append((player_name, log))

  # Run the day phase which consists of the debate and voting
  def run_day_phase(self):
    for idx in range(MAX_DEBATE_TURNS):
      next_speaker = self.get_next_speaker()
      if not next_speaker:
        raise ValueError("get_next_speaker did not return a valid player.")

      player = self.state.players[next_speaker]
      dialogue, log = player.debate()
      if dialogue is None:
        raise ValueError(
            f"{next_speaker} did not return a valid dialouge from debate()."
        )

      self.this_round_log.debate.append((next_speaker, log))
      self.this_round.debate.append([next_speaker, dialogue])
      tqdm.tqdm.write(f"{next_speaker} ({player.role}): {dialogue}")

      for name in self.this_round.players:
        player = self.state.players[name]
        if player.gamestate:
          player.gamestate.update_debate(next_speaker, dialogue)
        else:
          raise ValueError(f"{name}.gamestate needs to be initialized.")

      if idx == MAX_DEBATE_TURNS - 1 or RUN_SYNTHETIC_VOTES:
        votes, vote_logs = self.run_voting()
        self.this_round.votes.append(votes)
        self.this_round_log.votes.append(vote_logs)

    for player, vote in self.this_round.votes[-1].items():
      tqdm.tqdm.write(f"{player} voted to remove {vote}")

  # Conduct a vote among players to exile someone
  def run_voting(self):
    vote_log = []
    votes = {}

    with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
      player_votes = {
          name: executor.submit(self.state.players[name].vote)
          for name in self.this_round.players
      }

      for player_name, vote_task in player_votes.items():
        vote, log = vote_task.result()
        vote_log.append(VoteLog(player_name, vote, log))

        if vote is not None:
          votes[player_name] = vote
        else:
          self.this_round.votes.append(votes)
          self.this_round_log.votes.append(vote_log)
          raise ValueError(f"{player_name} vote did not return a valid player.")

    return votes, vote_log

  # Exile the player who received the most votes
  def exile(self):
    most_voted, vote_count = Counter(
        self.this_round.votes[-1].values()
    ).most_common(1)[0]

    if vote_count > len(self.this_round.players) / 2:
      self.this_round.exiled = most_voted

    if self.this_round.exiled is not None:
      exiled_player = self.this_round.exiled
      self.this_round.players.remove(exiled_player)
      announcement = (
          f"The majority voted to remove {exiled_player} from the game."
      )
    else:
      announcement = (
          "A majority vote was not reached, so no one was removed from the"
          " game."
      )

    for name in self.this_round.players:
      player = self.state.players[name]
      if player.gamestate and self.this_round.exiled is not None:
        player.gamestate.remove_player(self.this_round.exiled)
      player.add_announcement(announcement)

    tqdm.tqdm.write(announcement)

  # Resolve the night phase
  def resolve_night_phase(self):
    if self.this_round.eliminated != self.this_round.protected:
      eliminated_player = self.this_round.eliminated
      self.this_round.players.remove(eliminated_player)
      announcement = (
          f"The Werewolves removed {eliminated_player} from the game during the"
          " night."
      )
    else:
      announcement = "No one was removed from the game during the night."
    tqdm.tqdm.write(announcement)

    for name in self.this_round.players:
      player = self.state.players[name]
      if player.gamestate:
        player.gamestate.remove_player(self.this_round.eliminated)
      player.add_announcement(announcement)

  # Run a single round of the game
  def run_round(self):
    self.state.rounds.append(Round())
    self.logs.append(RoundLog())

    self.this_round.players = (
        list(self.state.players.keys())
        if self.current_round_num == 0
        else self.state.rounds[self.current_round_num - 1].players.copy()
    )

    for action, message in [
        (self.eliminate, "The Werewolves are picking someone to remove from the game."),
        (self.protect, "The Doctor is protecting someone."),
        (self.unmask, "The Seer is investigating someone."),
        (self.resolve_night_phase, ""),
        (self.check_for_winner, "Checking for a winner after Night Phase."),
        (self.run_day_phase, "The Players are debating and voting."),
        (self.exile, ""),
        (self.check_for_winner, "Checking for a winner after Day Phase."),
        (self.run_summaries, "The Players are summarizing the debate."),
    ]:
      tqdm.tqdm.write(message)
      action()

      if self.state.winner:
        tqdm.tqdm.write(f"Round {self.current_round_num} is complete.")
        self.this_round.success = True
        return

    tqdm.tqdm.write(f"Round {self.current_round_num} is complete.")
    self.this_round.success = True

  # Determine the winner of the game
  def get_winner(self):
    active_wolves = set(self.this_round.players) & set(w.name for w in self.state.werewolves)
    active_villagers = set(self.this_round.players) - active_wolves
    if len(active_wolves) >= len(active_villagers):
      return "Werewolves"
    return "Villagers" if not active_wolves else ""

  # Check if there is a winner and update the state accordingly
  def check_for_winner(self):
    self.state.winner = self.get_winner()
    if self.state.winner:
      tqdm.tqdm.write(f"The winner is {self.state.winner}!")

  def _auto_save(self):
    """Save game state if log_directory is set."""
    if self.log_directory:
      try:
        from playground import game_logging
        game_logging.save_game(self.state, self.logs, self.log_directory)
        tqdm.tqdm.write(f"💾 Auto-saved game state")
      except Exception as e:
        tqdm.tqdm.write(f"⚠️ Could not auto-save: {e}")

  # Run the entire Werewolf game and return the winner
  def run_game(self):
    while not self.state.winner:
      tqdm.tqdm.write(f"STARTING ROUND: {self.current_round_num}")
      self.run_round()
      
      # Auto-save after each round
      self._auto_save()
      
      for name in self.this_round.players:
        if self.state.players[name].gamestate:
          self.state.players[name].gamestate.round_number = (
              self.current_round_num + 1
          )
          self.state.players[name].gamestate.clear_debate()
      self.current_round_num += 1

    tqdm.tqdm.write("Game is complete!")
    return self.state.winner