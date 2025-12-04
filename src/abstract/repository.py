"""Base repository class for data access layer.

Provides generic CRUD operations with transaction support, pagination,
filtering, and both FastAPI DI and ARQ worker compatibility.
"""

from collections.abc import Sequence
from typing import Annotated
from typing import Any
from typing import Self

from fastapi import Depends
from sqlalchemy import ColumnElement
from sqlalchemy import delete
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from .entity import Entity
from src.core.database import get_session
from src.exceptions import NotFoundException


# Type alias for filter conditions
type FilterType = ColumnElement[bool] | bool


class Repository[EntityT: Entity]:
    """Base repository with generic CRUD operations.

    This class provides a complete data access layer with:
    - Single and bulk read operations
    - Single and bulk create operations
    - Single and bulk update operations
    - Single and bulk delete operations
    - Pagination support
    - Count and existence checks
    - Transaction support for cross-repository operations

    Usage with FastAPI (automatic dependency injection):
        ```python
        from typing import Annotated
        from fastapi import Depends

        class UserRepository(Repository[User]):
            pass  # Entity type auto-detected from generic parameter

        @app.get("/users/{user_id}")
        async def get_user(
            user_id: UUID,
            user_repo: Annotated[UserRepository, Depends()],
        ):
            return await user_repo.get_one(User.pk == user_id)
        ```

    Usage with ARQ workers (manual instantiation):
        ```python
        async def process_user_task(ctx: dict, user_id: UUID):
            async with get_session_context() as session:
                repo = UserRepository(session)
                user = await repo.get_one(User.pk == user_id)
                # ... process user
        ```

    Transaction support (multiple repositories sharing session):
        ```python
        async with get_session_context() as session:
            user_repo = UserRepository(session)
            profile_repo = ProfileRepository(session)

            user = await user_repo.create(email="test@example.com")
            await profile_repo.create(user_id=user.pk, bio="Hello")

            await session.commit()  # Both operations in one transaction
        ```

    Attributes:
        _entity: The SQLAlchemy entity class (auto-detected from type parameter).
        _session: The async database session.
    """

    _entity: type[Entity]
    __orig_bases__: tuple[type, ...]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Extract entity type when a subclass is defined."""
        super().__init_subclass__(**kwargs)
        cls._entity = cls.__orig_bases__[0].__args__[0]

    def __init__(
        self,
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session (from DI or context manager).
        """
        self._session = session

    def with_session(self, session: AsyncSession) -> Self:
        """Create a new repository instance with different session.

        Useful for transaction operations across repositories.

        Args:
            session: New async session to use.

        Returns:
            New repository instance with the given session.
        """
        return self.__class__(session)

    # =========================================================================
    # COUNT AND EXISTS OPERATIONS
    # =========================================================================

    async def count(self, *filters: FilterType) -> int:
        """Count entities matching optional filters.

        Args:
            *filters: Optional SQLAlchemy filter conditions.

        Returns:
            Number of matching entities.

        Example:
            total_users = await repo.count()
            active_users = await repo.count(User.is_locked == False)
        """
        stmt = select(func.count()).select_from(self._entity)

        if filters:
            stmt = stmt.where(*filters)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def exists(self, *filters: FilterType) -> bool:
        """Check if any entity exists matching filters.

        Args:
            *filters: SQLAlchemy filter conditions.

        Returns:
            True if at least one entity matches.

        Example:
            if await repo.exists(User.email == email):
                raise ConflictException("Email already registered")
        """
        stmt = select(exists().where(*filters))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================
    async def select_one(self, *filters: FilterType) -> EntityT | None:
        """Get a single entity by filters, return None if not found.

        Args:
            *filters: SQLAlchemy filter conditions.

        Returns:
            The matching entity or None.

        Raises:
            MultipleResultsFound: If more than one entity matches.

        Example:
            user = await repo.select_one(User.email == "test@example.com")
            if user is None:
                # Handle not found case
        """
        stmt = select(self._entity).where(*filters)
        result = await self._session.execute(stmt)
        # one_or_none() raises MultipleResultsFound if more than one result
        return result.scalars().one_or_none()

    async def get_one(self, *filters: FilterType) -> EntityT:
        """Get a single entity by filters, raise if not found.

        Args:
            *filters: SQLAlchemy filter conditions.

        Returns:
            The matching entity.

        Raises:
            NotFoundException: If no entity matches the filters.
            MultipleResultsFound: If more than one entity matches.

        Example:
            user = await repo.get_one(User.pk == user_id)
            user = await repo.get_one(User.email == "test@example.com")
        """
        from sqlalchemy.exc import NoResultFound

        stmt = select(self._entity).where(*filters)
        result = await self._session.execute(stmt)
        try:
            # one() raises NoResultFound or MultipleResultsFound
            return result.scalars().one()
        except NoResultFound:
            raise NotFoundException(
                entity_name=self._entity.__name__,
                entity_id=str(filters),
            ) from None

    async def get_by_id(self, pk: int) -> EntityT:
        """Get a single entity by primary key, raise if not found.

        Args:
            pk: Primary key value.

        Returns:
            The matching entity.

        Raises:
            NotFoundException: If no entity matches the primary key.

        Example:
            user = await repo.get_by_id(user_id)
        """
        return await self.get_one(self._entity.pk == pk)

    async def select_all(self, *filters: FilterType) -> Sequence[EntityT]:
        """Select all entities matching optional filters.

        Args:
            *filters: Optional SQLAlchemy filter conditions.

        Returns:
            Sequence of matching entities (maybe empty).

        Example:
            all_users = await repo.select_all()
            active_users = await repo.select_all(User.is_locked == False)
        """
        stmt = select(self._entity)
        if filters:
            stmt = stmt.where(*filters)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def paginate(
        self,
        *filters: FilterType,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[EntityT], int]:
        """Get paginated entities with total count.

        Args:
            *filters: Optional SQLAlchemy filter conditions.
            limit: Maximum number of items to return.
            offset: Number of items to skip.

        Returns:
            Tuple of (entities, total_count).

        Example:
            users, total = await repo.paginate(
                User.is_locked == False,
                limit=10,
                offset=20
            )
        """
        # Build query
        stmt = select(self._entity)
        if filters:
            stmt = stmt.where(*filters)

        # Get total count
        total = await self.count(*filters)

        # Get paginated results
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        entities = result.scalars().all()

        return entities, total

    async def get_by_ids(self, ids: Sequence[int]) -> Sequence[EntityT]:
        """Get multiple entities by their primary keys.

        Args:
            ids: Sequence of primary key values.

        Returns:
            Sequence of matching entities (order not guaranteed).

        Example:
            users = await repo.get_by_ids([1, 2, 3])
        """
        if not ids:
            return []

        stmt = select(self._entity).where(self._entity.pk.in_(ids))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # CREATE OPERATIONS
    # =========================================================================

    async def create(self, *, flush: bool = True, **kwargs: Any) -> EntityT:
        """Create a single entity.

        Args:
            flush: Whether to flush immediately (default True).
            **kwargs: Entity field values.

        Returns:
            The created entity.

        Example:
            user = await repo.create(
                email="test@example.com",
                first_name="John",
                last_name="Doe"
            )
        """
        instance = self._entity(**kwargs)
        self._session.add(instance)

        if flush:
            await self._session.flush()

        return instance

    async def create_from_entity(self, entity: EntityT, *, flush: bool = True) -> EntityT:
        """Add an existing entity instance to the session.

        Args:
            entity: The entity instance to persist.
            flush: Whether to flush immediately (default True).

        Returns:
            The persisted entity.

        Example:
            user = User(email="test@example.com", first_name="John")
            user = await repo.create_from_entity(user)
        """
        self._session.add(entity)

        if flush:
            await self._session.flush()

        return entity

    async def bulk_create(
        self,
        entities_data: Sequence[dict[str, Any]],
        *,
        flush: bool = True,
    ) -> Sequence[EntityT]:
        """Create multiple entities in bulk.

        Args:
            entities_data: Sequence of dictionaries with entity field values.
            flush: Whether to flush immediately (default True).

        Returns:
            Sequence of created entities.

        Example:
            users = await repo.bulk_create([
                {"email": "user1@example.com", "first_name": "User1"},
                {"email": "user2@example.com", "first_name": "User2"},
            ])
        """
        instances = [self._entity(**data) for data in entities_data]
        self._session.add_all(instances)

        if flush:
            await self._session.flush()

        return instances

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    async def update(
        self,
        entity: EntityT,
        *,
        flush: bool = True,
        **kwargs: Any,
    ) -> EntityT:
        """Update a single entity with given values.

        Args:
            entity: The entity to update.
            flush: Whether to flush immediately (default True).
            **kwargs: Field values to update.

        Returns:
            The updated entity.

        Example:
            user = await repo.get_one(User.pk == user_id)
            user = await repo.update(user, first_name="Jane", last_name="Smith")
        """
        for key, value in kwargs.items():
            setattr(entity, key, value)

        if flush:
            await self._session.flush()

        return entity

    async def update_by_filters(
        self,
        values: dict[str, Any],
        *filters: FilterType,
        flush: bool = True,
    ) -> int:
        """Update multiple entities matching filters.

        Args:
            values: Dictionary of field values to update.
            *filters: SQLAlchemy filter conditions.
            flush: Whether to flush immediately (default True).

        Returns:
            Number of rows updated.

        Example:
            count = await repo.update_by_filters(
                {"is_locked": True},
                User.last_login < cutoff_date
            )
        """
        stmt = update(self._entity).where(*filters).values(**values)
        result = await self._session.execute(stmt)

        if flush:
            await self._session.flush()

        return result.rowcount

    async def bulk_update(
        self,
        entities: Sequence[EntityT],
        values: dict[str, Any],
        *,
        flush: bool = True,
    ) -> Sequence[EntityT]:
        """Update multiple entity instances with same values.

        Args:
            entities: Sequence of entities to update.
            values: Dictionary of field values to update.
            flush: Whether to flush immediately (default True).

        Returns:
            The updated entities.

        Example:
            users = await repo.select_all(User.is_staff == True)
            users = await repo.bulk_update(users, {"language": Language.EN})
        """
        for entity in entities:
            for key, value in values.items():
                setattr(entity, key, value)

        if flush:
            await self._session.flush()

        return entities

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    async def delete(self, entity: EntityT, *, flush: bool = True) -> None:
        """Delete a single entity.

        Args:
            entity: The entity to delete.
            flush: Whether to flush immediately (default True).

        Example:
            user = await repo.get_one(User.pk == user_id)
            await repo.delete(user)
        """
        await self._session.delete(entity)

        if flush:
            await self._session.flush()

    async def delete_by_filters(self, *filters: FilterType, flush: bool = True) -> int:
        """Delete multiple entities matching filters.

        Args:
            *filters: SQLAlchemy filter conditions (required).
            flush: Whether to flush immediately (default True).

        Returns:
            Number of rows deleted.

        Example:
            count = await repo.delete_by_filters(
                User.is_locked == True,
                User.last_login < cutoff_date,
            )
        """
        if not filters:
            raise ValueError("At least one filter is required for bulk delete")
        stmt = delete(self._entity).where(*filters)
        result = await self._session.execute(stmt)

        if flush:
            await self._session.flush()

        return result.rowcount

    async def bulk_delete(self, entities: Sequence[EntityT], *, flush: bool = True) -> None:
        """Delete multiple entity instances.

        Args:
            entities: Sequence of entities to delete.
            flush: Whether to flush immediately (default True).

        Example:
            inactive_users = await repo.select_all(User.last_login < cutoff)
            await repo.bulk_delete(inactive_users)
        """
        for entity in entities:
            await self._session.delete(entity)

        if flush:
            await self._session.flush()

    # =========================================================================
    # REFRESH OPERATIONS
    # =========================================================================

    async def refresh(self, entity: EntityT, attribute_names: Sequence[str] | None = None) -> EntityT:
        """Refresh entity from database.

        Args:
            entity: The entity to refresh.
            attribute_names: Optional list of attribute names to refresh.

        Returns:
            The refreshed entity.

        Example:
            user = await repo.refresh(user)
            user = await repo.refresh(user, ["profile", "settings"])
        """
        await self._session.refresh(entity, attribute_names=attribute_names)
        return entity
