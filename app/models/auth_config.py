"""Shared authentication configuration persisted in the application database."""

from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String, Text

from app.db.session import Base


class AuthConfig(Base):  # type: ignore
    """Singleton row controlling database-backed OIDC configuration."""

    __tablename__ = "auth_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_auth_config_singleton"),)

    id = Column(Integer, primary_key=True, nullable=False)
    oidc_enabled = Column(Boolean, nullable=False)
    oidc_issuer = Column(String, nullable=True)
    oidc_client_id = Column(String, nullable=True)
    oidc_client_secret_encrypted = Column(Text, nullable=True)
    oidc_scope = Column(String, nullable=False)
