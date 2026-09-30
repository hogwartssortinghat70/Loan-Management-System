from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)

    loans = relationship("Loan", back_populates="customer")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    principal = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    emi = Column(Float, nullable=False)
    # Total amount repayable (EMI x tenure), i.e. principal + interest
    total_payable = Column(Float, nullable=False)
    outstanding_amount = Column(Float, nullable=False)
    status = Column(String, default="ACTIVE", nullable=False)

    customer = relationship("Customer", back_populates="loans")
    payments = relationship("Payment", back_populates="loan", order_by="Payment.id")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    paid_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    loan = relationship("Loan", back_populates="payments")
