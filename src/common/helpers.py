import json
from typing import Dict, Any, Union

from redis.typing import FieldT


def serialize_value(v: Union[FieldT, Dict[str, Any]]) -> FieldT:
    if isinstance(v, dict):
        return json.dumps(v)
    return v
