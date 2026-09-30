from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(min_length=5, max_length=20)

    @field_validator("name", "phone")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str


class LoanCreate(BaseModel):
    customer_id: int
    principal: float = Field(gt=0, le=1_000_000_000)
    interest_rate: float = Field(ge=0, le=100)
    tenure_months: int = Field(gt=0, le=600)


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    principal: float
    interest_rate: float
    tenure_months: int
    emi: float
    total_payable: float
    outstanding_amount: float
    status: str


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    amount: float
    paid_at: datetime
