"""Repository pattern for database access."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.config.settings import settings
from src.storage.models import Base, Report, MarketSnapshot, RegimeHistory, Document, PromptTemplate


class Database:
    """Database connection manager."""

    _instance: "Database | None" = None
    _engine = None
    _session_factory = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Initialize database connection."""
        if self._engine is None:
            kwargs: dict = {"echo": settings.debug}
            if "sqlite" in settings.database_url:
                kwargs["connect_args"] = {"check_same_thread": False}
            else:
                kwargs["pool_size"] = 5
                kwargs["max_overflow"] = 10
            self._engine = create_async_engine(settings.database_url, **kwargs)
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def create_tables(self) -> None:
        """Create all tables."""
        if self._engine:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    def get_session(self) -> AsyncSession:
        """Get a database session."""
        if self._session_factory is None:
            raise RuntimeError("Database not connected")
        return self._session_factory()


class ReportRepository:
    """Repository for report operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, report: "Report") -> Report:
        """Save a report to the database."""
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_by_id(self, report_id: str) -> Report | None:
        """Get a report by its ID."""
        result = await self.session.execute(
            select(Report).where(Report.report_id == report_id)
        )
        return result.scalar_one_or_none()

    async def list_recent(
        self,
        limit: int = 10,
        offset: int = 0,
        level: int | None = None,
    ) -> list[Report]:
        """List recent reports."""
        query = select(Report).order_by(desc(Report.created_at))

        if level is not None:
            query = query.where(Report.level == level)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, level: int | None = None) -> int:
        """Count total reports."""
        from sqlalchemy import func

        query = select(func.count(Report.id))
        if level is not None:
            query = query.where(Report.level == level)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def delete(self, report_id: str) -> bool:
        """Delete a report."""
        report = await self.get_by_id(report_id)
        if report:
            await self.session.delete(report)
            await self.session.commit()
            return True
        return False


class SnapshotRepository:
    """Repository for market snapshot operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        """Save a snapshot to the database."""
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest(self) -> MarketSnapshot | None:
        """Get the most recent snapshot."""
        result = await self.session.execute(
            select(MarketSnapshot)
            .order_by(desc(MarketSnapshot.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_range(
        self,
        start: datetime,
        end: datetime | None = None,
    ) -> list[MarketSnapshot]:
        """Get snapshots within a date range."""
        if end is None:
            end = datetime.now(UTC)

        result = await self.session.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.timestamp >= start)
            .where(MarketSnapshot.timestamp <= end)
            .order_by(MarketSnapshot.timestamp)
        )
        return list(result.scalars().all())

    async def get_daily_snapshots(self, days: int = 30) -> list[MarketSnapshot]:
        """Get one snapshot per day for the last N days."""
        start = datetime.now(UTC) - timedelta(days=days)
        return await self.get_range(start)


class RegimeRepository:
    """Repository for regime history operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, regime: RegimeHistory) -> RegimeHistory:
        """Save a regime classification."""
        self.session.add(regime)
        await self.session.commit()
        await self.session.refresh(regime)
        return regime

    async def get_latest(self) -> RegimeHistory | None:
        """Get the most recent regime classification."""
        result = await self.session.execute(
            select(RegimeHistory)
            .order_by(desc(RegimeHistory.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(self, days: int = 90) -> list[RegimeHistory]:
        """Get regime history for the last N days."""
        start = datetime.now(UTC) - timedelta(days=days)

        result = await self.session.execute(
            select(RegimeHistory)
            .where(RegimeHistory.timestamp >= start)
            .order_by(RegimeHistory.timestamp)
        )
        return list(result.scalars().all())


class DocumentRepository:
    """Repository for uploaded research document metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, document: Document) -> Document:
        """Save a document record."""
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def get_by_id(self, document_id: str) -> Document | None:
        """Get a document by its unique document_id."""
        result = await self.session.execute(
            select(Document).where(Document.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        """List documents ordered by upload date (newest first)."""
        result = await self.session.execute(
            select(Document)
            .order_by(desc(Document.uploaded_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total documents."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Document.id))
        )
        return result.scalar_one()

    async def delete(self, document_id: str) -> bool:
        """Delete a document by its document_id."""
        doc = await self.get_by_id(document_id)
        if doc:
            await self.session.delete(doc)
            await self.session.commit()
            return True
        return False


class PromptTemplateRepository:
    """Repository for prompt template operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, template: PromptTemplate) -> PromptTemplate:
        """Save a prompt template."""
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def get_by_id(self, template_id: str) -> PromptTemplate | None:
        """Get a template by its unique template_id."""
        result = await self.session.execute(
            select(PromptTemplate).where(PromptTemplate.template_id == template_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PromptTemplate]:
        """List templates ordered by creation date (defaults first, then newest)."""
        result = await self.session.execute(
            select(PromptTemplate)
            .order_by(desc(PromptTemplate.is_default), desc(PromptTemplate.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total templates."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(PromptTemplate.id))
        )
        return result.scalar_one()

    async def delete(self, template_id: str) -> bool:
        """Delete a template by its template_id."""
        tpl = await self.get_by_id(template_id)
        if tpl:
            await self.session.delete(tpl)
            await self.session.commit()
            return True
        return False
