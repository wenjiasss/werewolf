from typing import Any, Dict
import dataclasses
import jinja2
import utils
from utils import Deserializable
import apis
from game.config import RETRIES


# ============================================================================
# LLM LOG
# ============================================================================

# Records a single LLM interaction for analysis and debugging
@dataclasses.dataclass
class LmLog(Deserializable):
    prompt: str
    raw_resp: str
    result: Any

    @classmethod
    def from_json(cls, data: Dict[Any, Any]):
        return cls(**data)


# ============================================================================
# PROMPT FORMATTING
# ============================================================================

# Renders a Jinja2 template with game state to create the final prompt
def format_prompt(prompt_template, worldstate):
    return jinja2.Template(prompt_template).render(worldstate)


# ============================================================================
# GENERATION WITH RETRY LOGIC
# ============================================================================

# Generates a response from the LLM with validation and retry logic
def generate(
    prompt_template,
    response_schema,
    worldstate,
    model,
    temperature=1.0,
    allowed_values=None,
    result_key=None):
    prompt = format_prompt(prompt_template, worldstate)
    raw_responses = []
    
    for _ in range(RETRIES):
        raw_resp = None
        try:
            # Call LLM API with structured output
            raw_resp = apis.generate(
                model=model,
                prompt=prompt,
                response_schema=response_schema,
                temperature=temperature,
                disable_recitation=True,  # Prevent model from reciting training data
                disable_safety_check=True,  # Game context requires discussing "elimination"
            )
            
            # Parse JSON response
            result = utils.parse_json(raw_resp)
            log = LmLog(prompt=prompt, raw_resp=raw_resp, result=result)

            # Extract specific key if requested (e.g., just the "vote" field)
            if result and result_key:
                result = result.get(result_key)

            # Validate against allowed values if provided
            if allowed_values is None or result in allowed_values:
                return result, log

        except Exception as e:
            print(f"Retrying due to Exception: {e}")
        
        # Increase temperature for next retry to get more diverse outputs
        temperature = min(1.0, temperature + 0.2)
        raw_responses.append(raw_resp)

    # All retries failed - return None with concatenated responses for debugging
    return None, LmLog(
        prompt=prompt, 
        raw_resp="-------".join(raw_responses), 
        result=None
    )
