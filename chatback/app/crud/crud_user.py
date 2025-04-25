from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from .base import CRUDBase
import logging

logger = logging.getLogger(__name__)

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def authenticate(self, db: AsyncSession, *, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password"""
        try:
            logger.info(f"Attempting authentication for username: {username}")
            result = await db.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"No user found with username: {username}")
                return None

            logger.info(f"Found user: {user.username}, verifying password")
            if not verify_password(password, user.hashed_password):
                logger.warning("Password verification failed")
                return None

            logger.info("Authentication successful")
            return user
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """Get user by username, eagerly loading the group relationship."""
        stmt = (
            select(User)
            .options(selectinload(User.group))
            .filter(User.username == username)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create new user"""
        try:
            create_data = obj_in.model_dump()
            create_data["hashed_password"] = get_password_hash(create_data.pop("password"))
            db_obj = User(**create_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    async def update(self, db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> User:
        """Update existing user"""
        update_data = obj_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        return await super().update(db=db, db_obj=db_obj, obj_in=update_data)

crud_user = CRUDUser(User) 