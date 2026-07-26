from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SmsLog(Base):
    __tablename__ = "sms_logs"
    __table_args__ = (
        Index("ix_sms_logs_customer", "customer_id"),
        Index("ix_sms_logs_reservation_created", "reservation_id", "created_at"),
        Index("ix_sms_logs_status_created", "status", "created_at"),
        Index(
            "ix_sms_logs_provider_external_message_id",
            "provider",
            "external_message_id",
            unique=True,
            postgresql_where=text("external_message_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    reservation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="sms_logs")
    job = relationship("Job", back_populates="sms_logs")
    reservation = relationship("Reservation", back_populates="sms_logs")
