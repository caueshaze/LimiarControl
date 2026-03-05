from pydantic import BaseModel

class UserSearchRead(BaseModel):
    id: str
    displayName: str
    username: str
