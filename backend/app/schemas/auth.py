from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=1, max_length=200)


class UserRead(BaseModel):
    id: int
    username: str
    name: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
