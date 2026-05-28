import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ContractFile(Base):
    __tablename__ = "contract_files"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outline_preview: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extraction_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    product_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    fee_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    lock_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscription_xlsx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_b_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
