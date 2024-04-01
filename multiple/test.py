import dataclasses
import typing
import json

@dataclasses.dataclass
class Payload:
    id: int
    method: str
    params: typing.Dict


payload = Payload(75, 'subscribeTrades', {'symbol': 'ETHBTC'})
print(payload.__dataclass_fields__)
print(json.dumps(payload.__dataclass_fields__))