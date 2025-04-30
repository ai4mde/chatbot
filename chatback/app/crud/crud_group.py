from sqlalchemy.future import select
from typing import Optional

# Use AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.schemas.group import GroupCreate, GroupUpdate
from .base import CRUDBase
import logging

logger = logging.getLogger(__name__)


class CRUDGroup(CRUDBase[Group, GroupCreate, GroupUpdate]):

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Group]:
        """Get group by name."""
        result = await db.execute(select(Group).filter(Group.name == name))
        return result.scalar_one_or_none()

    # Add any group-specific methods here if needed in the future.
    # For now, the base methods for create, get, get_multi, update, remove are sufficient.
    pass


crud_group = CRUDGroup(Group)
