"""Shared authentication configuration persisted in the application database."""

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuthConfig(Base):  # type: ignore
    """Singleton row controlling database-backed OIDC configuration."""

    __tablename__ = "auth_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_auth_config_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    oidc_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    oidc_issuer: Mapped[str | None] = mapped_column(String, nullable=True)
    oidc_client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    oidc_client_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    oidc_scope: Mapped[str] = mapped_column(String, nullable=False)
