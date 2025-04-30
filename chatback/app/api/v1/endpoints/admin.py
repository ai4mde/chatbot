from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from app import crud, models
from app.api import deps
from app.schemas.user import User, UserCreate, UserUpdate
from app.schemas.group import Group, GroupCreate, GroupUpdate
from app.schemas.qdrant import (
    QdrantCollectionInfo,
    QdrantCollectionList,
    QdrantCollectionCreate,
    QdrantStatus,
)
from app.services.vector_store import qdrant_manager  # Import the global instance

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[
        Depends(deps.get_current_admin_user)
    ],  # Protect all routes in this router
)

# === User Management ===


@router.get("/users", response_model=List[User])
async def read_users(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve all users (Admin only), including their group information."""
    stmt = (
        select(models.User)
        .options(selectinload(models.User.group))
        .offset(skip)
        .limit(limit)
        .order_by(models.User.id)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserCreate,
) -> Any:
    """Create new user (Admin only)."""
    user = await crud.crud_user.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists.",
        )
    user = await crud.crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists.",
        )
    # Ensure group exists if group_id is provided
    if user_in.group_id:
        group = await crud.crud_group.get(db, id=user_in.group_id)
        if not group:
            raise HTTPException(
                status_code=404, detail=f"Group with id {user_in.group_id} not found."
            )

    new_user = await crud.crud_user.create(db=db, obj_in=user_in)
    return new_user


@router.put("/users/{user_id}", response_model=User)
async def update_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
    user_in: UserUpdate,
) -> Any:
    """Update a user (Admin only)."""
    user = await crud.crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail="The user with this id does not exist"
        )
    # Ensure group exists if group_id is being updated
    if user_in.group_id is not None:
        group = await crud.crud_group.get(db, id=user_in.group_id)
        if not group:
            raise HTTPException(
                status_code=404, detail=f"Group with id {user_in.group_id} not found."
            )

    updated_user = await crud.crud_user.update(db=db, db_obj=user, obj_in=user_in)
    return updated_user


@router.get("/users/{user_id}", response_model=User)
async def read_user_by_id(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
) -> Any:
    """Get a specific user by id (Admin only)."""
    user = await crud.crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail="The user with this id does not exist"
        )
    return user


@router.delete("/users/{user_id}", response_model=User)
async def delete_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
) -> Any:
    """Delete a user (Admin only)."""
    logger.info(f"Admin attempting to delete user id {user_id}")
    user = await crud.crud_user.get(db=db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Add check to prevent self-deletion?
    # current_admin = Depends(deps.get_current_admin_user) # Need to resolve how to get this here if needed
    # if current_admin.id == user_id:
    #     raise HTTPException(status_code=403, detail="Admins cannot delete themselves")
    deleted_user = await crud.crud_user.remove(db=db, id=user_id)
    logger.info(f"User id {user_id} deleted successfully by admin.")
    return deleted_user


# === Group Management ===


@router.get("/groups", response_model=List[Group])
async def read_groups(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve all groups (Admin only)."""
    groups = await crud.crud_group.get_multi(db, skip=skip, limit=limit)
    return groups


@router.post("/groups", response_model=Group, status_code=status.HTTP_201_CREATED)
async def create_group(
    *,
    db: AsyncSession = Depends(deps.get_db),
    group_in: GroupCreate,
) -> Any:
    """Create new group (Admin only)."""
    group = await crud.crud_group.get_by_name(
        db, name=group_in.name
    )  # Assumes get_by_name exists
    if group:
        raise HTTPException(
            status_code=400,
            detail="A group with this name already exists.",
        )
    new_group = await crud.crud_group.create(db=db, obj_in=group_in)
    return new_group


@router.put("/groups/{group_id}", response_model=Group)
async def update_group(
    *,
    db: AsyncSession = Depends(deps.get_db),
    group_id: int,
    group_in: GroupUpdate,
) -> Any:
    """Update a group (Admin only)."""
    group = await crud.crud_group.get(db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=404, detail="The group with this id does not exist"
        )
    updated_group = await crud.crud_group.update(db=db, db_obj=group, obj_in=group_in)
    return updated_group


@router.get("/groups/{group_id}", response_model=Group)
async def read_group_by_id(
    *,
    db: AsyncSession = Depends(deps.get_db),
    group_id: int,
) -> Any:
    """Get a specific group by id (Admin only)."""
    group = await crud.crud_group.get(db, id=group_id)
    if not group:
        raise HTTPException(
            status_code=404, detail="The group with this id does not exist"
        )
    return group


@router.delete("/groups/{group_id}", response_model=Group)
async def delete_group(
    *,
    db: AsyncSession = Depends(deps.get_db),
    group_id: int,
) -> Any:
    """Delete a group (Admin only)."""
    logger.info(f"Admin attempting to delete group id {group_id}")
    group = await crud.crud_group.get(db=db, id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # Check if group has users? Add constraint or check here if needed.
    deleted_group = await crud.crud_group.remove(db=db, id=group_id)
    logger.info(f"Group id {group_id} deleted successfully by admin.")
    return deleted_group


# === Vector DB Management ===


@router.get("/vector-db/status", response_model=QdrantStatus)
async def get_vector_db_status():
    """Get the connection status of the Qdrant vector database."""
    if not qdrant_manager:
        # If manager failed to initialize at startup
        return QdrantStatus(
            connected=False, error="QdrantManager failed to initialize."
        )

    status_data = qdrant_manager.get_status()
    return QdrantStatus(**status_data)


@router.get("/vector-db/collections", response_model=QdrantCollectionList)
async def get_vector_db_collections():
    """List all collections in the Qdrant vector database."""
    if not qdrant_manager or not qdrant_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Qdrant service is not connected or available.",
        )

    collections_data = qdrant_manager.get_all_collections_info()
    # Map the dict list to the Pydantic model list
    collections = [QdrantCollectionInfo(**c) for c in collections_data]
    return QdrantCollectionList(collections=collections)


@router.post(
    "/vector-db/collections",
    response_model=QdrantCollectionInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_vector_db_collection(
    *,
    collection_in: QdrantCollectionCreate,
):
    """Create a new collection in the Qdrant vector database."""
    if not qdrant_manager or not qdrant_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Qdrant service is not connected or available.",
        )

    success = qdrant_manager.create_collection(name=collection_in.name)
    if not success:
        # Check if it failed because it already exists or another reason
        existing = False
        try:
            # A bit hacky, but check if it exists now
            collections = qdrant_manager.get_all_collections_info()
            if any(c["name"] == collection_in.name for c in collections):
                existing = True
        except Exception:
            pass  # Ignore errors during check

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection '{collection_in.name}' already exists.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create collection '{collection_in.name}'. Check backend logs.",
            )

    # Fetch the details of the newly created collection to return
    # Wrap in try-except in case fetching fails immediately after creation
    try:
        collection_info = qdrant_manager.get_collection_info(
            collection_name=collection_in.name
        )
        if collection_info:
            # Map the detailed info to our response schema
            return QdrantCollectionInfo(
                name=collection_in.name,
                status=collection_info.status.value,
                points_count=collection_info.points_count,
                vectors_count=collection_info.vectors_count,
            )
        else:
            # Should ideally exist if creation succeeded, but handle unlikely case
            logger.error(
                f"Collection '{collection_in.name}' created but failed to retrieve info immediately."
            )
            # Return basic info
            return QdrantCollectionInfo(name=collection_in.name, status="unknown")
    except Exception as e:
        logger.error(
            f"Error retrieving info for newly created collection '{collection_in.name}': {e}",
            exc_info=True,
        )
        # Return basic info on error
        return QdrantCollectionInfo(name=collection_in.name, status="unknown")


@router.delete(
    "/vector-db/collections/{collection_name}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_vector_db_collection(
    collection_name: str,
):
    """Delete a specific collection from the Qdrant vector database."""
    if not qdrant_manager or not qdrant_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Qdrant service is not connected or available.",
        )

    if collection_name == qdrant_manager.collection_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Deleting the primary chat collection ('{collection_name}') is forbidden.",
        )

    success = qdrant_manager.delete_collection(name=collection_name)
    if not success:
        # Check if it failed because it didn't exist or another reason
        not_found = False
        try:
            # Check if it still exists (indicating deletion failed for other reasons)
            collections = qdrant_manager.get_all_collections_info()
            if not any(c["name"] == collection_name for c in collections):
                not_found = True
        except Exception:
            pass  # Ignore errors during check

        if not_found:
            # Collection already didn't exist, treat as success (idempotent) or raise 404?
            # Raising 404 seems more informative if the user expected it to exist.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete collection '{collection_name}'. Check backend logs.",
            )

    # No body needed for 204 response
    return None


# === Other Admin Endpoints ===


@router.get("/stats/overview")
async def get_admin_stats(db: AsyncSession = Depends(deps.get_db)):
    user_count = await crud.crud_user.count(db)
    group_count = await crud.crud_group.count(db)

    # Get Qdrant info using new manager method
    qdrant_connected = False
    total_collections = 0
    total_vectors = 0
    if qdrant_manager and qdrant_manager.is_connected:
        qdrant_connected = True
        try:
            collections_data = qdrant_manager.get_all_collections_info()
            total_collections = len(collections_data)
            total_vectors = sum(c.get("points_count", 0) or 0 for c in collections_data)
        except Exception as e:
            logger.error(f"Error getting Qdrant stats: {e}", exc_info=True)

    return {
        "user_count": user_count,
        "group_count": group_count,
        "qdrant_connected": qdrant_connected,
        "qdrant_collections": total_collections,
        "qdrant_total_vectors": total_vectors,
    }
