import json

from redis.typing import FieldT

from src.common.typing import RedisSerializableValue


def serialize_value(v: RedisSerializableValue) -> FieldT:
    if isinstance(v, dict):
        return json.dumps(v)
    return v
