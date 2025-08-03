from typing import Union, Dict, Any

from redis.typing import FieldT

RedisSerializableValue = Union[FieldT, Dict[str, Any]]
