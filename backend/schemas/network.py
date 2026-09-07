from pydantic import BaseModel

class NetworkConnection(BaseModel):
    remote: str
    service: str
    status: str

class NetworkStatus(BaseModel):
    local_connections: list[NetworkConnection]
    external_connections: list[NetworkConnection]
    blocked_attempts: list[dict]
    sovereign: bool
