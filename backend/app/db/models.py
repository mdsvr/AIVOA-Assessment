from datetime import datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="pending_triage")

    complaint_source: Mapped[str | None] = mapped_column(String, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String, nullable=True)

    product_name: Mapped[str | None] = mapped_column(String, nullable=True)
    product_strength: Mapped[str | None] = mapped_column(String, nullable=True)
    batch_lot_number: Mapped[str | None] = mapped_column(String, nullable=True)
    manufacturing_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    quantity_affected: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String, nullable=True)

    complaint_type: Mapped[str | None] = mapped_column(String, nullable=True)
    complaint_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    initial_severity: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[str | None] = mapped_column(String, nullable=True)

    completeness_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    risk_classification: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("complaints.id"), nullable=True
    )
    raw_extraction: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    documents: Mapped[list["ComplaintDocument"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )


class ComplaintDocument(Base):
    __tablename__ = "complaint_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"))
    filename: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    extracted_text: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="documents")
