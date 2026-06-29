from datetime import datetime, timezone
import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="operator", nullable=False)  # "owner" or "operator"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # "active", "paused", "completed", "interrupted"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=get_utc_now, 
        onupdate=get_utc_now, 
        nullable=False
    )

    # Relationships
    wallet: Mapped["CampaignWallet"] = relationship("CampaignWallet", back_populates="campaign", cascade="all, delete-orphan")
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")
    logs: Mapped[List["AgentLog"]] = relationship("AgentLog", back_populates="campaign", cascade="all, delete-orphan")
    deliverables: Mapped[List["Deliverable"]] = relationship("Deliverable", back_populates="campaign", cascade="all, delete-orphan")


class CampaignWallet(Base):
    __tablename__ = "campaign_wallets"

    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), primary_key=True)
    budget: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    cost_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_liquidated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationship
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="wallet")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Validation & Status
    qualification_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)  # "verified", "undeliverable", "catch_all", "unknown"
    outreach_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # "pending", "email_sent", "replied", "bounced", "declined"
    
    # Vector Embeddings (1536 dims for standard OpenAI embeddings)
    vector_profile = mapped_column(Vector(1536), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationship
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="leads")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("campaigns.id"), index=True, nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)  # "executive", "deep_research", "deal_closer", "qa"
    log_level: Mapped[str] = mapped_column(String(20), default="info", nullable=False)  # "info", "warning", "error"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_reflection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Vector Embeddings for reflection logs retrieval
    vector_log = mapped_column(Vector(1536), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationship
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="logs")


class ModuleRegistry(Base):
    __tablename__ = "module_registry"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Module Name, e.g. "StockMarketModule"
    path: Mapped[str] = mapped_column(String(255), nullable=False)  # Local path to dynamic python script
    config_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # Configuration parameter requirements
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class StagedPrompt(Base):
    __tablename__ = "staging_prompt_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # E.g. "executive_decision_prompt"
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="staged", nullable=False)  # "pinned", "staged"
    benchmark_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class StripeEvent(Base):
    __tablename__ = "stripe_processed_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)  # Stripe Event ID for idempotency verification
    processed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class SenderDomain(Base):
    __tablename__ = "sender_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=100, nullable=False)  # 0 means blocked/rate-limited
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class SystemConfig(Base):
    __tablename__ = "system_configurations"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted Fernet string
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class Deliverable(Base):
    __tablename__ = "campaign_deliverables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), index=True, nullable=False)
    lead_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("leads.id"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "Dental Clinic SEO Strategy"
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "email", "blog_post", "ad_copy"
    content_body: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown text
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # DALL-E generated asset link
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # "draft", "qa_pending", "approved", "manual_review_pending"
    refinement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Safe cap tracker
    qa_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="deliverables")
    lead: Mapped[Optional["Lead"]] = relationship("Lead")

