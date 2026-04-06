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
