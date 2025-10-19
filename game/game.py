from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from model.model import Round, RoundLog, VoteLog
from game.config import MAX_DEBATE_TURNS, RUN_SYNTHETIC_VOTES
import random
import tqdm

# Gets all the keys with the highest value in a dictionary
def get_max_bids(dict):
    max_value = max(dict.values())
    max_keys = [key for key, value in dict.items() if value == max_value]
    return max_keys

# Orchestrates the Werewolf game - runs night/day phases, manages turns, determines winner
class GameMaster:
    def __init__(self, state, num_threads=1, log_directory=None):
        self.state = state
        self.current_round_num = len(self.state.rounds) if self.state.rounds else 0
        self.num_threads = num_threads  # For parallel LLM calls
        self.logs = []  # List of RoundLog objects
        self.log_directory = log_directory  # For auto-saving after each round

    @property
    def this_round(self):
        # Auto-updates when state.rounds changes
        return self.state.rounds[self.current_round_num]

    @property
    def this_round_log(self):
        # Auto-updates when logs changes
        return self.logs[self.current_round_num]
    
    # Werewolves choose a player to eliminate during night phase
    def eliminate(self):
        werewolves_alive = [w for w in self.state.werewolves if w.name in self.this_round.players]
        wolf = random.choice(werewolves_alive)  # Pick one werewolf to make the decision
        eliminated, log = wolf.eliminate()
        self.this_round_log.eliminate = log

        if eliminated is not None:
            self.this_round.eliminated = eliminated
            tqdm.tqdm.write(f"{wolf.name} eliminated {eliminated}")
            # Both werewolves observe the elimination
            for wolf in werewolves_alive:
                wolf._add_observation(
                    "During the"
                    f" night, {'we' if len(werewolves_alive) > 1 else 'I'} decided to"
                    f" eliminate {eliminated}"
                )
        else:
            raise ValueError("Eliminate did not return a valid player")

    # Doctor chooses a player to protect during night phase
    def protect(self):
        if self.state.doctor.name not in self.this_round.players:
            return  # Doctor no longer in the game

        protect, log = self.state.doctor.save()
        self.this_round_log.protect = log

        if protect is not None:
            self.this_round.protected = protect
            tqdm.tqdm.write(f"{self.state.doctor.name} protected {protect}")
        else:
            # Model failed to return valid player, choose randomly as fallback
            protect = random.choice(self.this_round.players)
            self.this_round.protected = protect
            tqdm.tqdm.write(f"Doctor action failed, randomly protecting {protect}")

    # Seer chooses a player to unmask during night phase
    def unmask(self):
        if self.state.seer.name not in self.this_round.players:
            return  # Seer no longer in the game

        unmask, log = self.state.seer.unmask()
        self.this_round_log.investigate = log

        if unmask is not None:
            self.this_round.unmasked = unmask
            self.state.seer.reveal_and_update(unmask, self.state.players[unmask].role)
        else:
            # Model failed, choose randomly from uninvestigated players
            options = [p for p in self.this_round.players 
                      if p != self.state.seer.name and p not in self.state.seer.previously_unmasked]
            if options:
                unmask = random.choice(options)
                self.this_round.unmasked = unmask
                self.state.seer.reveal_and_update(unmask, self.state.players[unmask].role)
                tqdm.tqdm.write(f"Seer action failed, randomly investigating {unmask}")

    # Gets the bid for a specific player
    def _get_bid(self, player_name):
        player = self.state.players[player_name]
        bid, log = player.bid()
        if bid is None:
            raise ValueError(
                f"{player_name} did not return a valid bid. Find the raw response"
                " in the bid field in the log"
            )
        if bid > 1:  # Only log notable bids
            tqdm.tqdm.write(f"{player_name} bid: {bid}")
        return bid, log

    # Determine the next speaker based on bids (highest bidder speaks)
    def get_next_speaker(self):
        previous_speaker, previous_dialogue = (self.this_round.debate[-1] if self.this_round.debate else (None, None))

        # Collect bids from all players except the previous speaker
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
        # Prioritize players mentioned in previous dialogue if there's a tie
        if previous_dialogue:
            potential_speakers.extend(
                [name for name in potential_speakers if name in previous_dialogue]
            )

        random.shuffle(potential_speakers)
        return random.choice(potential_speakers)

    # Collect summaries from all players after the debate
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

    # Run the day phase: debate and voting
    def run_day_phase(self):
        for idx in range(MAX_DEBATE_TURNS):
            # Bidding determines who speaks
            next_speaker = self.get_next_speaker()
            if not next_speaker:
                raise ValueError("get_next_speaker did not return a valid player")

            # Player speaks
            player = self.state.players[next_speaker]
            dialogue, log = player.debate()
            if dialogue is None:
                raise ValueError(
                    f"{next_speaker} did not return a valid dialogue from debate()"
                )

            self.this_round_log.debate.append((next_speaker, log))
            self.this_round.debate.append([next_speaker, dialogue])
            tqdm.tqdm.write(f"{next_speaker} ({player.role}): {dialogue}")

            # Update all players' game views with the new dialogue
            for name in self.this_round.players:
                player = self.state.players[name]
                if player.gamestate:
                    player.gamestate.update_debate(next_speaker, dialogue)
                else:
                    raise ValueError(f"{name}.gamestate needs to be initialized")

            # Collect role assessments after each speaker
            self.collect_role_assessments_during_debate()

            # Run voting (either after every turn for metrics or just at the end)
            if idx == MAX_DEBATE_TURNS - 1 or RUN_SYNTHETIC_VOTES:
                votes, vote_logs = self.run_voting()
                self.this_round.votes.append(votes)
                self.this_round_log.votes.append(vote_logs)

        # Log final votes
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
                    raise ValueError(f"{player_name} vote did not return a valid player")

        return votes, vote_log

    # Exile the player who received the most votes (if majority reached)
    def exile(self):
        most_voted, vote_count = Counter(
            self.this_round.votes[-1].values()
        ).most_common(1)[0]

        # Require majority vote to exile
        if vote_count > len(self.this_round.players) / 2:
            self.this_round.exiled = most_voted

        if self.this_round.exiled is not None:
            exiled_player = self.this_round.exiled
            self.this_round.players.remove(exiled_player)
            announcement = (
                f"The majority voted to remove {exiled_player} from the game"
            )
        else:
            announcement = (
                "A majority vote was not reached, so no one was removed from the"
                " game"
            )

        # Update all players' game views
        for name in self.this_round.players:
            player = self.state.players[name]
            if player.gamestate and self.this_round.exiled is not None:
                player.gamestate.remove_player(self.this_round.exiled)
            player.add_announcement(announcement)

        tqdm.tqdm.write(announcement)

    # Resolve the night phase: remove eliminated player unless protected
    def resolve_night_phase(self):
        if self.this_round.eliminated != self.this_round.protected:
            eliminated_player = self.this_round.eliminated
            self.this_round.players.remove(eliminated_player)
            announcement = (
                f"The Werewolves removed {eliminated_player} from the game during the"
                " night"
            )
        else:
            announcement = "No one was removed from the game during the night"
        tqdm.tqdm.write(announcement)

        # Update all players' game views
        for name in self.this_round.players:
            player = self.state.players[name]
            if player.gamestate:
                player.gamestate.remove_player(self.this_round.eliminated)
            player.add_announcement(announcement)

    # Collect role assessments from all players after night phase
    def collect_role_assessments_post_night(self):
        tqdm.tqdm.write("Collecting role assessments after night actions...")
        
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            assessment_tasks = {
                name: executor.submit(self.state.players[name].assess_roles)
                for name in self.this_round.players
            }
            
            for player_name, assessment_task in assessment_tasks.items():
                result, log = assessment_task.result()
                if result is not None:
                    self.this_round.role_assessments_post_night[player_name] = result
                    self.this_round_log.role_assessments_post_night.append((player_name, log))
                else:
                    tqdm.tqdm.write(f"{player_name} failed to provide role assessment")

    # Collect role assessments from all players after a debate turn
    def collect_role_assessments_during_debate(self):
        tqdm.tqdm.write("Collecting role assessments after debate turn...")
        
        assessment_logs = []
        assessments = {}
        
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            assessment_tasks = {
                name: executor.submit(self.state.players[name].assess_roles)
                for name in self.this_round.players
            }
            
            for player_name, assessment_task in assessment_tasks.items():
                result, log = assessment_task.result()
                if result is not None:
                    assessments[player_name] = result
                    assessment_logs.append((player_name, log))
                else:
                    tqdm.tqdm.write(f"{player_name} failed to provide role assessment")
        
        self.this_round.role_assessments_during_debate.append(assessments)
        self.this_round_log.role_assessments_during_debate.append(assessment_logs)

    # Run a single round of the game
    def run_round(self):
        self.state.rounds.append(Round())
        self.logs.append(RoundLog())

        # Initialize players for this round (all players for round 0, survivors for later rounds)
        self.this_round.players = (
            list(self.state.players.keys())
            if self.current_round_num == 0
            else self.state.rounds[self.current_round_num - 1].players.copy()
        )

        # Execute round phases in order
        for action, message in [
            (self.eliminate, "The Werewolves are picking someone to remove from the game"),
            (self.protect, "The Doctor is protecting someone"),
            (self.unmask, "The Seer is investigating someone"),
            (self.resolve_night_phase, ""),
            (self.collect_role_assessments_post_night, ""),
            (self.check_for_winner, "Checking for a winner after Night Phase"),
            (self.run_day_phase, "The Players are debating and voting"),
            (self.exile, ""),
            (self.check_for_winner, "Checking for a winner after Day Phase"),
            (self.run_summaries, "The Players are summarizing the debate"),
        ]:
            tqdm.tqdm.write(message)
            action()

            # Exit early if game is over
            if self.state.winner:
                tqdm.tqdm.write(f"Round {self.current_round_num} is complete")
                self.this_round.success = True
                return

        tqdm.tqdm.write(f"Round {self.current_round_num} is complete")
        self.this_round.success = True

    # Determine the winner of the game
    def get_winner(self):
        active_wolves = set(self.this_round.players) & set(w.name for w in self.state.werewolves)
        active_villagers = set(self.this_round.players) - active_wolves
        
        # Werewolves win if they equal or outnumber villagers
        if len(active_wolves) >= len(active_villagers):
            return "Werewolves"
        # Villagers win if all werewolves are eliminated
        return "Villagers" if not active_wolves else ""

    # Check if there is a winner and update the state
    def check_for_winner(self):
        self.state.winner = self.get_winner()
        if self.state.winner:
            tqdm.tqdm.write(f"The winner is {self.state.winner}!")

    # Save game state after each round if log_directory is set
    def _auto_save(self):
        if self.log_directory:
            try:
                from game import game_logging
                game_logging.save_game(self.state, self.logs, self.log_directory)
                tqdm.tqdm.write(f"Auto-saved game state")
            except Exception as e:
                tqdm.tqdm.write(f"Could not auto-save: {e}")

    # Run the entire Werewolf game until there's a winner
    def run_game(self):
        while not self.state.winner:
            tqdm.tqdm.write(f"STARTING ROUND: {self.current_round_num}")
            self.run_round()
            
            # Save game state after each round
            self._auto_save()
            
            # Update game views for next round
            for name in self.this_round.players:
                if self.state.players[name].gamestate:
                    self.state.players[name].gamestate.round_number = (
                        self.current_round_num + 1
                    )
                    self.state.players[name].gamestate.clear_debate()
            self.current_round_num += 1

        tqdm.tqdm.write("Game is complete!")
        return self.state.winner
