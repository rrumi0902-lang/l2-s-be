from pydantic import BaseModel

class UserModel(BaseModel):
    email: str
    username: str
    password: str