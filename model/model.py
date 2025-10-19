import enum
import json
import random
from typing import Any, Dict, List, Tuple
from model.lm import LmLog, generate
from model.prompts import ACTION_PROMPTS_AND_SCHEMAS
from utils import Deserializable
from game.config import MAX_DEBATE_TURNS, NUM_PLAYERS

# ============================================================================
# ROLE CONSTANTS
# ============================================================================

VILLAGER = "Villager"
WEREWOLF = "Werewolf"
SEER = "Seer"
DOCTOR = "Doctor"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Groups observations by round and formats them for display
def group_and_format_observations(observations):
    grouped = {}
    for obs in observations:
        round_num = int(obs.split(":", 1)[0].split()[1])
        obs_text = obs.split(":", 1)[1].strip().replace('"', "")
        grouped.setdefault(round_num, []).append(obs_text)

    formatted_obs = []
    for round_num, round_obs in sorted(grouped.items()):
        formatted_round = f"Round {round_num}:\n"
        formatted_round += "\n".join(f"   - {obs}" for obs in round_obs)
        formatted_obs.append(formatted_round)

    return formatted_obs


# ============================================================================
# JSON SERIALIZATION
# ============================================================================

# Custom JSON encoder that handles nested classes and enums
class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, enum.Enum):
            return o.value
        if isinstance(o, set):
            return list(o)
        return o.__dict__

# Converts an object to a dictionary using the custom JSON encoder
def to_dict(o):
    return json.loads(JsonEncoder().encode(o))


# ============================================================================
# GAME VIEW
# ============================================================================

# Represents the game state from a single player's perspective
class GameView:
    def __init__(self, round_number, current_players, other_wolf=None):
        self.round_number = round_number
        self.current_players = current_players
        self.debate: List[tuple[str, str]] = []
        self.other_wolf = other_wolf  # Only used by Werewolves

    # Adds a new debate entry from a speaker
    def update_debate(self, author, dialogue):
        self.debate.append((author, dialogue))

    # Clears debate history (called at start of new round)
    def clear_debate(self):
        self.debate.clear()

    # Removes a player from the current players list
    def remove_player(self, player_to_remove):
        if player_to_remove not in self.current_players:
            print(f"Warning: Player {player_to_remove} not in current players: {self.current_players}")
        self.current_players.remove(player_to_remove)

    def to_dict(self):
        return to_dict(self)

    @classmethod
    def from_json(cls, data):
        return cls(**data)


# ============================================================================
# PLAYER BASE CLASS
# ============================================================================

# Base class for all player types
class Player(Deserializable):
    def __init__(self, name, role, model=None, personality=""):
        self.name = name
        self.role = role
        self.personality = personality
        self.model = model  # LLM model identifier
        self.observations = []  # Private game history visible only to this player
        self.bidding_rationale = ""  # Why they want to speak
        self.gamestate = None  # GameView instance

    # Sets up the player's view of the game state
    def initialize_game_view(self, round_number, current_players, other_wolf=None):
        self.gamestate = GameView(round_number, current_players, other_wolf)

    # Adds an observation to the player's private history
    def _add_observation(self, observation):
        if not self.gamestate:
            raise ValueError("GameView not initialized. Call initialize_game_view() first")
        self.observations.append(f"Round {self.gamestate.round_number}: {observation}")

    # Adds a moderator announcement to observations
    def add_announcement(self, announcement):
        self._add_observation(f"Moderator Announcement: {announcement}")
    
    # Builds the game state dictionary for prompt rendering
    def _get_game_state(self):
        if not self.gamestate:
            raise ValueError("GameView not initialized. Call initialize_game_view() first")

        # Shuffle player list and mark self
        remaining_players = [
            f"{player} (You)" if player == self.name else player
            for player in self.gamestate.current_players
        ]
        random.shuffle(remaining_players)
        
        # Format debate with self-marking
        formatted_debate = [
            f"{author} (You): {dialogue}" if author == self.name else f"{author}: {dialogue}"
            for author, dialogue in self.gamestate.debate
        ]

        formatted_observations = group_and_format_observations(self.observations)

        return {
            "name": self.name,
            "role": self.role,
            "round": self.gamestate.round_number,
            "observations": formatted_observations,
            "remaining_players": ", ".join(remaining_players),
            "debate": formatted_debate,
            "bidding_rationale": self.bidding_rationale,
            "debate_turns_left": MAX_DEBATE_TURNS - len(formatted_debate),
            "personality": self.personality,
            "num_players": NUM_PLAYERS,
            "num_villagers": NUM_PLAYERS - 4,  # Total - 2 Werewolves - 1 Seer - 1 Doctor
        }

    # Generates an action by calling the LLM with the appropriate prompt
    def _generate_action(self, action, options=None):
        game_state = self._get_game_state()
        if options:
            game_state["options"] = (", ").join(options)
        prompt_template, response_schema = ACTION_PROMPTS_AND_SCHEMAS[action]

        # Determine if this action needs validation against allowed values
        result_key, allowed_values = (
            (action, options)
            if action in ["vote", "remove", "investigate", "protect", "bid"]
            else (None, None)
        )

        # Use lower temperature for constrained choices, higher for creative responses
        temperature = 0.5 if allowed_values else 1.0

        return generate(
            prompt_template,
            response_schema,
            game_state,
            model=self.model,
            temperature=temperature,
            allowed_values=allowed_values,
            result_key=result_key,
        )
    
    # Player votes to exile someone during the day phase
    def vote(self):
        if not self.gamestate:
            raise ValueError("GameView not initialized. Call initialize_game_view() first")
        
        # Can vote for anyone except self
        options = [
            player for player in self.gamestate.current_players
            if player != self.name
        ]
        random.shuffle(options)
        vote, log = self._generate_action("vote", options)
        
        # Record vote in observations after debate concludes
        if vote is not None and len(self.gamestate.debate) == MAX_DEBATE_TURNS:
            self._add_observation(f"After the debate, I voted to remove {vote} from the game")
        return vote, log
    
    # Player bids to speak in the debate (0-4 scale)
    def bid(self):
        bid, log = self._generate_action("bid", options=["0", "1", "2", "3", "4"])
        if bid is not None:
            bid = int(bid)
            self.bidding_rationale = log.result.get("reasoning", "")
        return bid, log

    # Player makes a public statement in the debate
    def debate(self):
        result, log = self._generate_action("debate", [])
        if result is not None:
            say = result.get("say", None)
            return say, log
        return result, log

    # Player summarizes the round to form memories
    def summarize(self):
        result, log = self._generate_action("summarize", [])
        if result is not None:
            summary = result.get("summary", None)
            if summary is not None:
                summary = summary.strip('"')
                self._add_observation(f"Summary: {summary}")
            return summary, log
        return result, log

    # Player internally assesses what role they think each other player is (for metrics only, doesn't affect gameplay)
    def assess_roles(self):
        result, log = self._generate_action("assess_roles", [])
        return result, log

    def to_dict(self):
        return to_dict(self)

    @classmethod
    def from_json(cls, data):
        name = data["name"]
        role = data["role"]
        model = data.get("model", None)
        o = cls(name=name, role=role, model=model)
        o.gamestate = data.get("gamestate", None)
        o.bidding_rationale = data.get("bidding_rationale", "")
        o.observations = data.get("observations", [])
        return o


# ============================================================================
# VILLAGER
# ============================================================================

# A regular Villager with no special powers
class Villager(Player):
    def __init__(self, name, model=None, personality=None):
        super().__init__(name=name, role=VILLAGER, model=model, personality=personality)

    @classmethod
    def from_json(cls, data):
        name = data["name"]
        model = data.get("model", None)
        o = cls(name=name, model=model)
        o.gamestate = data.get("gamestate", None)
        o.bidding_rationale = data.get("bidding_rationale", "")
        o.observations = data.get("observations", [])
        return o


# ============================================================================
# WEREWOLF
# ============================================================================

# A Werewolf who eliminates players at night
class Werewolf(Player):
    def __init__(self, name, model=None, personality=None):
        super().__init__(name=name, role=WEREWOLF, model=model, personality=personality)
    
    # Extends base game state with werewolf-specific context
    def _get_game_state(self, **kwargs):
        state = super()._get_game_state(**kwargs)
        state["werewolf_context"] = self._get_werewolf_context()
        return state

    # Werewolf chooses a player to eliminate during the night phase
    def eliminate(self):
        if not self.gamestate:
            raise ValueError("GameView not initialized. Call initialize_game_view() first")

        # Can eliminate anyone except self and the other werewolf
        options = [
            player for player in self.gamestate.current_players
            if player != self.name and player != self.gamestate.other_wolf
        ]
        random.shuffle(options)
        eliminate, log = self._generate_action("remove", options)
        return eliminate, log

    # Generates context about the other werewolf for prompt injection
    def _get_werewolf_context(self):
        if not self.gamestate:
            raise ValueError("GameView not initialized. Call initialize_game_view() first")

        if self.gamestate.other_wolf in self.gamestate.current_players:
            context = f"\n- The other Werewolf is {self.gamestate.other_wolf}"
        else:
            context = (
                f"\n- The other Werewolf, {self.gamestate.other_wolf}, was exiled by "
                "the Villagers. Only you remain"
            )
        return context

    @classmethod
    def from_json(cls, data):
        name = data["name"]
        model = data.get("model", None)
        o = cls(name=name, model=model)
        o.gamestate = data.get("gamestate", None)
        o.bidding_rationale = data.get("bidding_rationale", "")
        o.observations = data.get("observations", [])
        return o


# ============================================================================
# SEER
# ============================================================================

# A Seer who can investigate one player's role each night
class Seer(Player):
    def __init__(self, name, model=None, personality=None):
        super().__init__(name=name, role=SEER, model=model, personality=personality)
        self.previously_unmasked = {}  # Tracks who they've investigated: {player_name: role}

    # Seer investigates a player during the night phase
    def unmask(self):
        if not self.gamestate:
            raise ValueError("GameView not initialized. Call initialize_game_view() first")

        # Can investigate anyone not yet investigated (except self)
        options = [
            player for player in self.gamestate.current_players
            if player != self.name and player not in self.previously_unmasked.keys()
        ]
        random.shuffle(options)
        return self._generate_action("investigate", options)

    # Records the result of investigating a player
    def reveal_and_update(self, player, role):
        self._add_observation(
            f"During the night, I decided to investigate {player} and learned they are a {role}"
        )
        self.previously_unmasked[player] = role

    @classmethod
    def from_json(cls, data):
        name = data["name"]
        model = data.get("model", None)
        o = cls(name=name, model=model)
        o.previously_unmasked = data.get("previously_unmasked", {})
        o.gamestate = data.get("gamestate", None)
        o.bidding_rationale = data.get("bidding_rationale", "")
        o.observations = data.get("observations", [])
        return o


# ============================================================================
# DOCTOR
# ============================================================================

# A Doctor who can protect one player from elimination each night
class Doctor(Player):
    def __init__(self, name, model=None, personality=None):
        super().__init__(name=name, role=DOCTOR, model=model, personality=personality)

    # Doctor protects a player during the night phase
    def save(self):
        if not self.gamestate:
            raise ValueError("GameView not initialized. Call initialize_game_view() first")

        # Can protect anyone, including self
        options = list(self.gamestate.current_players)
        random.shuffle(options)
        protected, log = self._generate_action("protect", options)
        if protected is not None:
            self._add_observation(f"During the night, I chose to protect {protected}")
        return protected, log

    @classmethod
    def from_json(cls, data):
        name = data["name"]
        model = data.get("model", None)
        o = cls(name=name, model=model)
        o.gamestate = data.get("gamestate", None)
        o.bidding_rationale = data.get("bidding_rationale", "")
        o.observations = data.get("observations", [])
        return o


# ============================================================================
# ROUND TRACKING
# ============================================================================

# Tracks all events and data for a single round of gameplay
class Round(Deserializable):
    def __init__(self):
        self.players: List[str] = []  # Players alive at start of round
        self.eliminated: str | None = None  # Who werewolves killed
        self.unmasked: str | None = None  # Who seer investigated
        self.protected: str | None = None  # Who doctor protected
        self.exiled: str | None = None  # Who was voted out
        self.debate: List[Tuple[str, str]] = []  # (speaker, dialogue) pairs
        self.votes: List[Dict[str, str]] = []  # Voting records
        self.bids: List[Dict[str, int]] = []  # Bidding records
        self.role_assessments_post_night: Dict[str, Any] = {}  # player_name -> assessment
        self.role_assessments_during_debate: List[Dict[str, Any]] = []  # One dict per debate turn
        self.success: bool = False  # Whether round completed without errors

    def to_dict(self):
        return to_dict(self)

    @classmethod
    def from_json(cls, data: Dict[Any, Any]):
        o = cls()
        o.players = data["players"]
        o.eliminated = data.get("eliminated", None)
        o.unmasked = data.get("unmasked", None)
        o.protected = data.get("protected", None)
        o.exiled = data.get("exiled", None)
        o.debate = data.get("debate", [])
        o.votes = data.get("votes", [])
        o.bids = data.get("bids", [])
        o.role_assessments_post_night = data.get("role_assessments_post_night", {})
        o.role_assessments_during_debate = data.get("role_assessments_during_debate", [])
        o.success = data.get("success", False)
        return o


# ============================================================================
# GAME STATE
# ============================================================================

# Tracks the complete state of a Werewolf game session
class State(Deserializable):
    def __init__(self, session_id, seer, doctor, villagers, werewolves):
        self.session_id: str = session_id
        self.seer: Seer = seer
        self.doctor: Doctor = doctor
        self.villagers: List[Villager] = villagers
        self.werewolves: List[Werewolf] = werewolves
        self.players: Dict[str, Player] = {
            player.name: player
            for player in self.villagers + self.werewolves + [self.doctor, self.seer]
        }
        self.rounds: List[Round] = []
        self.error_message: str = ""  # Set if game ends due to error
        self.winner: str = ""  # "Villager" or "Werewolf"

    def to_dict(self):
        return to_dict(self)

    @classmethod
    def from_json(cls, data):
        # Deserialize all player types
        werewolves = [Werewolf.from_json(w) for w in data.get("werewolves", [])]
        villagers = [Villager.from_json(v) for v in data.get("villagers", [])]
        doctor = Doctor.from_json(data.get("doctor"))
        seer = Seer.from_json(data.get("seer"))

        # Rebuild players dict
        players = {}
        for p in werewolves + villagers + [doctor, seer]:
            players[p.name] = p

        # Create state and restore rounds
        o = cls(data.get("session_id", ""), seer, doctor, villagers, werewolves)
        o.rounds = [Round.from_json(r) for r in data.get("rounds", [])]
        o.error_message = data.get("error_message", "")
        o.winner = data.get("winner", "")
        return o


# ============================================================================
# LOGGING STRUCTURES
# ============================================================================

# Records a single player's vote with their reasoning
class VoteLog(Deserializable):
    def __init__(self, player, voted_for, log):
        self.player = player
        self.voted_for = voted_for
        self.log = log  # LmLog containing reasoning

    def to_dict(self):
        return to_dict(self)

    @classmethod
    def from_json(cls, data):
        player = data.get("player", None)
        voted_for = data.get("voted_for", None)
        log = LmLog.from_json(data.get("log", None))
        return cls(player, voted_for, log)


# Contains all LLM interaction logs for a single round
class RoundLog(Deserializable):
    def __init__(self):
        self.eliminate = None  # LmLog from werewolf eliminate action
        self.investigate = None  # LmLog from seer investigate action
        self.protect = None  # LmLog from doctor protect action
        self.bid = []  # List[List[Tuple[str, LmLog]]] - bids for each debate turn
        self.debate = []  # List[Tuple[str, LmLog]] - debate statements
        self.votes = []  # List[List[VoteLog]] - votes after each debate turn
        self.summaries = []  # List[Tuple[str, LmLog]] - end of round summaries
        self.role_assessments_post_night = []  # List[Tuple[str, LmLog]]
        self.role_assessments_during_debate = []  # List[List[Tuple[str, LmLog]]]

    def to_dict(self):
        return to_dict(self)

    @classmethod
    def from_json(cls, data):
        o = cls()

        # Restore single action logs
        eliminate = data.get("eliminate", None)
        investigate = data.get("investigate", None)
        protect = data.get("protect", None)
        if eliminate:
            o.eliminate = LmLog.from_json(eliminate)
        if investigate:
            o.investigate = LmLog.from_json(investigate)
        if protect:
            o.protect = LmLog.from_json(protect)

        # Restore vote logs
        for votes in data.get("votes", []):
            v_logs = []
            o.votes.append(v_logs)
            for v in votes:
                v_logs.append(VoteLog.from_json(v))

        # Restore bid logs
        for r in data.get("bid", []):
            r_logs = []
            o.bid.append(r_logs)
            for player in r:
                r_logs.append((player[0], LmLog.from_json(player[1])))

        # Restore debate logs
        for player in data.get("debate", []):
            o.debate.append((player[0], LmLog.from_json(player[1])))

        # Restore summary logs
        for player in data.get("summaries", []):
            o.summaries.append((player[0], LmLog.from_json(player[1])))

        # Restore role assessment logs
        for player in data.get("role_assessments_post_night", []):
            o.role_assessments_post_night.append((player[0], LmLog.from_json(player[1])))

        for turn in data.get("role_assessments_during_debate", []):
            turn_logs = []
            o.role_assessments_during_debate.append(turn_logs)
            for player in turn:
                turn_logs.append((player[0], LmLog.from_json(player[1])))

        return o
