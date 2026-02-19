"""SQLAlchemy database models."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Report(Base):
    """Stored report model."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(256), nullable=False)
    level = Column(Integer, nullable=False)
    format = Column(String(32), nullable=False, default="markdown")
    content = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Report metadata
    regime = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_reports_created_at", "created_at"),
        Index("ix_reports_level", "level"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "title": self.title,
            "level": self.level,
            "format": self.format,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "regime": self.regime,
            "confidence": self.confidence,
        }


class MarketSnapshot(Base):
    """Stored market snapshot for time-series analysis."""

    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)

    # Equity indices
    spx = Column(Float, nullable=True)
    spx_change = Column(Float, nullable=True)
    nasdaq = Column(Float, nullable=True)
    nasdaq_change = Column(Float, nullable=True)
    vix = Column(Float, nullable=True)

    # Fixed income
    treasury_2y = Column(Float, nullable=True)
    treasury_10y = Column(Float, nullable=True)
    spread_2s10s = Column(Float, nullable=True)

    # FX
    dxy = Column(Float, nullable=True)
    eurusd = Column(Float, nullable=True)
    usdjpy = Column(Float, nullable=True)

    # Commodities
    gold = Column(Float, nullable=True)
    wti = Column(Float, nullable=True)

    # Crypto
    btc = Column(Float, nullable=True)
    btc_change = Column(Float, nullable=True)
    eth = Column(Float, nullable=True)

    # Full snapshot JSON
    full_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_snapshots_timestamp", "timestamp"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "spx": self.spx,
            "spx_change": self.spx_change,
            "vix": self.vix,
            "treasury_10y": self.treasury_10y,
            "spread_2s10s": self.spread_2s10s,
            "dxy": self.dxy,
            "gold": self.gold,
            "wti": self.wti,
            "btc": self.btc,
        }


class Document(Base):
    """Uploaded research document metadata (vectors live in ChromaDB)."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    title = Column(String(512), nullable=True)
    source_type = Column(String(64), default="pdf")  # pdf, excel, url
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer, nullable=True)  # bytes
    uploaded_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_documents_uploaded_at", "uploaded_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "filename": self.filename,
            "title": self.title,
            "source_type": self.source_type,
            "page_count": self.page_count,
            "chunk_count": self.chunk_count,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "metadata": self.metadata_json,
        }


class RegimeHistory(Base):
    """Historical market regime classifications."""

    __tablename__ = "regime_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    regime = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False)
    signals = Column(JSON, nullable=True)
    indicators = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_regime_timestamp", "timestamp"),
        Index("ix_regime_regime", "regime"),
    )
