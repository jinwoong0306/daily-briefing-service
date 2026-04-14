from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    created_at: datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class KeywordsUpdateRequest(BaseModel):
    keywords: list[str]
    expected_version: str | None = None

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            keyword = raw.strip()
            if not keyword:
                continue
            lower_keyword = keyword.lower()
            if lower_keyword in seen:
                continue
            seen.add(lower_keyword)
            cleaned.append(keyword)
        return cleaned


class KeywordsResponse(BaseModel):
    user_id: int
    keywords: list[str]
    version: str


class NotificationSettingsUpdateRequest(BaseModel):
    enabled: bool | None = None
    delivery_hour: int | None = Field(default=None, ge=0, le=23)
    delivery_minute: int | None = Field(default=None, ge=0, le=59)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    expected_version: str | None = None

    @field_validator("timezone")
    @classmethod
    def normalize_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("timezone cannot be empty")
        return normalized

    @property
    def has_any_field(self) -> bool:
        return any(
            value is not None
            for value in (self.enabled, self.delivery_hour, self.delivery_minute, self.timezone)
        )


class NotificationSettingsResponse(BaseModel):
    user_id: int
    enabled: bool
    delivery_hour: int
    delivery_minute: int
    timezone: str
    updated_at: datetime
    version: str
