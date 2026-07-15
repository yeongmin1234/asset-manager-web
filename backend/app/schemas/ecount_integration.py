from pydantic import BaseModel


class EcountAuthTestResponse(BaseModel):
    success: bool
    enabled: bool
    mode: str
    zone: str = ""
    authenticated: bool
    message: str
    response_time_ms: int
