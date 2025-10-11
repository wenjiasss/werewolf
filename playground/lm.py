from typing import Any, Dict, List, Optional
import dataclasses
import jinja2
from playground import utils
from playground.utils import Deserializable
from playground import apis
from playground.config import RETRIES

@dataclasses.dataclass
class LmLog(Deserializable):
    prompt: str
    raw_resp: str
    result: Any

    @classmethod
    def from_json(cls, data: Dict[Any, Any]):
        return cls(**data)


def format_prompt(prompt_template, worldstate):
    return jinja2.Template(prompt_template).render(worldstate)


def generate(
    prompt_template,
    response_schema,
    worldstate,
    model,
    temperature=1.0,
    allowed_values=None,
    result_key=None):
    """Generates text from the language model and parses the result.

    Args:
        prompt_template: The Jinja template for the prompt.
        response_schema: The schema for the expected response.
        worldstate: The world state to be rendered into the prompt.
        model: The language model to use.
        temperature: The sampling temperature for the language model.
        allowed_values: An optional list of allowed values for the result. If
          provided, the generation will retry until a result within the allowed
          values is obtained.
        result_key: An optional key to extract a specific value from the parsed
          result. If not provided, the entire parsed result is returned.

    Returns:
        A tuple containing the result (or None if unsuccessful) and the LmLog.
    """

    prompt = format_prompt(prompt_template, worldstate)
    raw_responses = []
    for _ in range(RETRIES):
        raw_resp = None
        try:
            raw_resp = apis.generate(
                model=model,
                prompt=prompt,
                response_schema=response_schema,
                temperature=temperature,
                disable_recitation=True,
                disable_safety_check=True,
            )
            result = utils.parse_json(raw_resp)
            log = LmLog(prompt=prompt, raw_resp=raw_resp, result=result)

            if result and result_key:
                result = result.get(result_key)

            if allowed_values is None or result in allowed_values:
                return result, log

        except Exception as e:
            print(f"Retrying due to Exception: {e}")
        temperature = min(1.0, temperature + 0.2)
        raw_responses.append(raw_resp)

    return None, LmLog(
        prompt=prompt, raw_resp="-------".join(raw_responses), result=None
    )
