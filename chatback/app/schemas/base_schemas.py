from pydantic import BaseModel, EmailStr


# Base schema for User, moved here to break circular imports
class UserBase(BaseModel):
    email: EmailStr
    username: str
