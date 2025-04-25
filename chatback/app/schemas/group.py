from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(GroupBase):
    pass

class GroupInDBBase(GroupBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class Group(GroupInDBBase):
    pass

class GroupWithUsers(GroupInDBBase):
    users: List["UserBase"]

class UserInGroup(BaseModel):
    id: int
    email: str
    username: str

    model_config = ConfigDict(from_attributes=True)

# Avoid circular imports by importing from the new base file
from app.schemas.base_schemas import UserBase

# Rebuild models that use forward references if necessary (might not be needed with direct import)
# GroupWithUsers.model_rebuild() # This might be removable if Pydantic handles it
# Or explicitly update forward refs if needed after importing UserBase:
GroupWithUsers.model_rebuild(force=True) 