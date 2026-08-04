"""User model — Hỗ trợ đa vai và đa công ty thành viên."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"          # Nhân viên gửi ticket
    TECHNICIAN = "technician"      # Kỹ thuật viên xử lý
    MANAGER = "manager"            # Quản lý phê duyệt HITL
    ADMIN = "admin"                # Quản trị hệ thống


class CompanyUnit(str, enum.Enum):
    REAL_ESTATE = "real_estate"    # BĐS X
    AUTOMOTIVE = "automotive"      # Xe X
    HEALTHCARE = "healthcare"      # Hệ thống Y tế X
    CORPORATE = "corporate"        # Tập đoàn (HQ)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE
    )
    company_unit: Mapped[CompanyUnit] = mapped_column(
        Enum(CompanyUnit), nullable=False, default=CompanyUnit.CORPORATE
    )
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)  # VIP → luôn HITL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tickets: Mapped[list] = relationship("Ticket", back_populates="submitter", foreign_keys="Ticket.submitter_id")
    assigned_tickets: Mapped[list] = relationship("Ticket", back_populates="assignee", foreign_keys="Ticket.assignee_id")
    audit_logs: Mapped[list] = relationship("AuditLog", back_populates="actor")

    def __repr__(self) -> str:
        return f"<User {self.username} [{self.role}/{self.company_unit}]>"
