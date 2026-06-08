from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    keywords: Mapped[list["UserKeyword"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_setting: Mapped["UserNotificationSetting | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    article_feedbacks: Mapped[list["UserArticleFeedback"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    saved_articles: Mapped[list["UserSavedArticle"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserKeyword(Base):
    __tablename__ = "user_keywords"
    __table_args__ = (UniqueConstraint("user_id", "keyword", name="uq_user_keyword"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    keyword: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="keywords")


class UserNotificationSetting(Base):
    __tablename__ = "user_notification_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    delivery_hour: Mapped[int] = mapped_column(nullable=False, default=8)
    delivery_minute: Mapped[int] = mapped_column(nullable=False, default=0)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Seoul")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="notification_setting")


class UserArticleFeedback(Base):
    __tablename__ = "user_article_feedbacks"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article_feedback"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    article_id: Mapped[int] = mapped_column(index=True)
    feedback_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="article_feedbacks")


class UserSavedArticle(Base):
    __tablename__ = "user_saved_articles"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_saved_article"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    article_id: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="saved_articles")
