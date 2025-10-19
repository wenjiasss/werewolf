# Prompt templates for Werewolf game actions
# Each prompt is a Jinja2 template that gets rendered with game state

# ============================================================================
# CORE CONTEXT SECTIONS
# ============================================================================

# Basic game rules shown to all players
GAME = """You are playing a digital version of the social deduction game Werewolf (also known as Mafia).

GAME RULES:
- Player Roles: {{num_players}} players - 2 Werewolves, 1 Seer, 1 Doctor, {{num_villagers}} Villagers.
- Rounds consist of two phases:
    - Night Phase: Werewolves remove a player. Seer identifies a player's role. Doctor saves a player. If no one is removed, the Doctor saved the Werewolf's target.
    - Day Phase: Players debate and vote to remove one player.
- Winning Conditions: Villagers win by voting out both Werewolves. Werewolves win when they outnumber the Villagers."""

# Current game state from the player's perspective
STATE = """GAME STATE:
- It is currently Round {{round}}. {% if round == 0 %}The game has just begun.{% endif %}
- You are {{name}} the {{role}}. {{werewolf_context}}
{% if personality -%}
- Personality: {{ personality }}
{% endif -%}
- Remaining players: {{remaining_players}}"""

# Player's private observations accumulated throughout the game
OBSERVATIONS = """{% if observations|length -%}YOUR PRIVATE OBSERVATIONS:
{% for turn in observations -%}
{{ turn }}
{% endfor %}
{% endif %}"""

# The debate history for the current round
DEBATE_SO_FAR_THIS_ROUND = """\nROUND {{round}} DEBATE:
{% if debate|length -%}
{% for turn in debate -%}
{{ turn }}
{% endfor -%}
{% else -%}
The debate has not begun.{% endif %}\n\n"""

# Standard prefix combining game rules, state, and observations
PREFIX = f"""{GAME}

{STATE}

{OBSERVATIONS}
""".strip()

# ============================================================================
# ACTION PROMPTS
# ============================================================================

# BIDDING: Players bid to determine speaking order in debate
BIDDING = (
    PREFIX
    + DEBATE_SO_FAR_THIS_ROUND
    + """CONTEXT: You will place a bid to speak next. Highest bidder speaks first.
- BID OPTIONS:
  0: I would like to observe and listen for now.
  1: I have some general thoughts to share.
  2: I have something critical to contribute.
  3: It is absolutely urgent for me to speak next.
  4: Someone has addressed me directly and I must respond.
- You have {{debate_turns_left}} chance(s) to speak left.

INSTRUCTIONS:
- Think strategically as {{name}} the {{role}}.
- Prioritize speaking only when you have something impactful to contribute.
{% if role == 'Werewolf' -%}
- Consider if speaking or staying silent better serves your goal of sowing chaos and avoiding detection.
{% else -%}
- If the discussion is off-track or you're under suspicion, consider speaking.
{% endif %}

```json
{
"reasoning": "string",  // How crucial is it for you to contribute right now? 1-2 sentences. Avoid violent language.
"bid": "string" // Your bid as a single number: "0" | "1" | "2" | "3" | "4"
}"
"""
)

BIDDING_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "bid": {"type": "string"},
    },
    "required": ["reasoning", "bid"],
}

# DEBATE: Player speaks publicly to the group
DEBATE = PREFIX + DEBATE_SO_FAR_THIS_ROUND + """INSTRUCTIONS:
- You are speaking next as {{name}} the {{role}}.
- Your thoughts on speaking: {{bidding_rationale}}
{% if role == 'Werewolf' -%}
- Your goal: sow chaos, evade detection, cast suspicion on Villagers.
- Make them doubt each other. Steer away from yourself and your fellow Werewolf.
- Appear helpful while undermining Villagers. Use deception strategically—claim roles, fabricate inconsistencies, but sparingly to avoid suspicion.
{% else -%}
- Your goal: uncover Werewolves and protect the Village.
- Scrutinize accusations, expose inconsistencies, call out suspicious behavior. Make bold accusations!
- Propose strategies and emphasize teamwork.
{% if role == 'Villager' -%}
- If someone reveals as Seer or Doctor, corroborate with what you know.
{% elif role in ['Seer', 'Doctor'] -%}
- Revealing your role is powerful but makes you a target. Weigh helping in secret vs. revealing crucial information.
{% endif -%}
{% endif %}

```json
{
  "reasoning": "string", // Your strategy: What do you want to achieve? Avoid violent language.
  "say": "string" // Your public statement. Be concise and persuasive. Respond directly to what others said. Don't repeat others or instructions.
}
"""

DEBATE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "say": {"type": "string"},
    },
    "required": ["reasoning", "say"],
}

# VOTE: Player privately votes to exile someone
VOTE = PREFIX + DEBATE_SO_FAR_THIS_ROUND + """INSTRUCTIONS:
- Decide who to vote out as {{name}} the {{role}}.
- Your vote is private and will not be revealed to others.
{% if role == 'Werewolf' -%}
- Target Villagers who threaten you, especially influential ones or those who might be Doctor/Seer.
- If Villagers suspect one of their own, join the chorus and pile on.
{% else -%}
- Look for inconsistencies, deflection, discord-sowing, or unusual silence.
{% endif -%}
- You must choose someone.

```json
{
  "reasoning": "string", // Explain your reasoning. Avoid violent language.
  "vote": "string" // Name of the player. Choose from: {{options}}
}"""

VOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "vote": {"type": "string"},
    },
    "required": ["reasoning", "vote"],
}

# INVESTIGATE: Seer's night action to learn a player's true role
INVESTIGATE = PREFIX + """INSTRUCTIONS:
- It is the Night Phase of Round {{round}}. As {{name}} the {{role}}, choose who to investigate.
{% if round == 0 -%}
- No information is available yet, so choose randomly.
{% else -%}
- Look for behavior deviating from typical villager patterns.
- Focus on influential players.
{% endif %}
- You must choose someone.

```json
{
"reasoning": "string", // Analyze the evidence and justify your decision.
"investigate": "string" // Name of the player. Choose from: {{options}}
}
"""

INVESTIGATE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "investigate": {"type": "string"},
    },
    "required": ["reasoning", "investigate"],
}

# ELIMINATE: Werewolf's night action to remove a player
ELIMINATE = PREFIX + """INSTRUCTIONS:
- It is the Night Phase of Round {{round}}. As {{name}} the {{role}}, choose who to remove.
{% if round == 0 -%}
- No information is available yet, so choose randomly.
{% else -%}
- Target influential Villagers who threaten your anonymity.
- Consider the risks of removing each player.
{% endif %}
- You must choose someone.

```json
{
"reasoning": "string", // Explain your reasoning step-by-step. Avoid violent language.
"remove": "string" // Name of the player. Choose from: {{options}}
}
"""

ELIMINATE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "remove": {"type": "string"},
    },
    "required": ["reasoning", "remove"],
}

# PROTECT: Doctor's night action to save a player
PROTECT = PREFIX + """INSTRUCTIONS:
- It is the Night Phase of Round {{round}}. As {{name}} the {{role}}, choose who to protect.
{% if round == 0 -%}
- No information is available yet, so choose randomly.
{% else -%}
- Consider who Werewolves might target.
- Prioritize crucial roles like the Seer and yourself.
{% endif %}
- You must choose someone.

```json
{
"reasoning": "string", // Analyze the evidence and justify your decision.
"protect": "string" // Name of the player. Choose from: {{options}}
}
"""

PROTECT_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "protect": {"type": "string"},
    },
    "required": ["reasoning", "protect"],
}

# SUMMARIZE: Player reflects on the round to form memories
SUMMARIZE = PREFIX + DEBATE_SO_FAR_THIS_ROUND + """INSTRUCTIONS:
- Reflect on the round's debate as {{name}} the {{role}}.
{% if role == 'Werewolf' -%}
- Note accusations against you and your ally, identify sympathetic or easily influenced players, and key roles to target.
{% else -%}
- Evaluate statement credibility: does it align with what you know?
- Analyze participation: contradictions? Hidden motives? Unusual silence?
- Identify potential allies, trustworthy players, or those who might be Seer/Doctor.
{% endif %}

```json
{
"reasoning": "string", // What should you remember and why is it important?
"summary": "string" // Summarize key points and noteworthy observations. Note as many players as you can—details matter. Be specific. Write from {{name}}'s perspective using "I" and "me."
} """

SUMMARIZE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["reasoning", "summary"],
}

# ASSESS_ROLES: Player internally evaluates each other player's role (used for metrics only)
ASSESS_ROLES = PREFIX + DEBATE_SO_FAR_THIS_ROUND + """INSTRUCTIONS:
- As {{name}} the {{role}}, assess whether each other player is a Villager or Werewolf.
- For each player, provide your best guess and confidence (1-100).
  - 1 = not confident at all, just guessing
  - 100 = absolutely certain
- Base assessments on behavior, statements, voting patterns, and any information you have.
{% if role == 'Werewolf' -%}
- Remember, you know {{werewolf_context}} - factor this into your assessments.
{% elif role == 'Seer' -%}
- You have investigated some players and know their true roles. Use this in your assessment.
{% endif %}
- IMPORTANT: Only assess Villager or Werewolf. Don't guess Seer or Doctor—classify as Villager if they seem good.

```json
{
  "reasoning": "string", // Briefly explain your thinking about who seems suspicious and why.
  "assessments": [ // For each other player (NOT yourself), provide an assessment
    {
      "player": "string", // Name of the player you're assessing
      "suspected_role": "string", // Either "Villager" or "Werewolf"
      "confidence": number // Your confidence level from 1-100
    }
  ]
}
```"""

ASSESS_ROLES_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "player": {"type": "string"},
                    "suspected_role": {
                        "type": "string",
                        "enum": ["Villager", "Werewolf"]
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["player", "suspected_role", "confidence"]
            }
        }
    },
    "required": ["reasoning", "assessments"],
}

# Maps action names to their (prompt_template, schema) pairs
ACTION_PROMPTS_AND_SCHEMAS = {
    "bid": (BIDDING, BIDDING_SCHEMA),
    "debate": (DEBATE, DEBATE_SCHEMA),
    "vote": (VOTE, VOTE_SCHEMA),
    "investigate": (INVESTIGATE, INVESTIGATE_SCHEMA),
    "remove": (ELIMINATE, ELIMINATE_SCHEMA),
    "protect": (PROTECT, PROTECT_SCHEMA),
    "summarize": (SUMMARIZE, SUMMARIZE_SCHEMA),
    "assess_roles": (ASSESS_ROLES, ASSESS_ROLES_SCHEMA),
}
