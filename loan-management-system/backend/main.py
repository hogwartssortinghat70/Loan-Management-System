from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, SessionLocal, engine

app = FastAPI(
    title="Loan Management System",
    description="Simple LMS for managing customers, loans and payments",
)

# Allow the Vite dev server to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "Loan Management System API is running"}


# =========================================================
# CUSTOMER APIs
# =========================================================

@app.post("/customers", response_model=schemas.CustomerOut, status_code=201)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Customer)
        .filter(models.Customer.email == customer.email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this email already exists")

    new_customer = models.Customer(
        name=customer.name, email=customer.email, phone=customer.phone
    )
    db.add(new_customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Customer with this email already exists")
    db.refresh(new_customer)
    return new_customer


@app.get("/customers", response_model=List[schemas.CustomerOut])
def get_customers(db: Session = Depends(get_db)):
    return db.query(models.Customer).order_by(models.Customer.id).all()


@app.get("/customers/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Deleting a customer with loans would leave orphaned loan records
    if customer.loans:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a customer who has loans",
        )

    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted successfully"}


# =========================================================
# LOAN APIs
# =========================================================

def calculate_emi(principal: float, annual_interest_rate: float, tenure_months: int) -> float:
    monthly_rate = annual_interest_rate / 12 / 100

    if monthly_rate == 0:
        return round(principal / tenure_months, 2)

    factor = (1 + monthly_rate) ** tenure_months
    emi = principal * monthly_rate * factor / (factor - 1)
    return round(emi, 2)


@app.post("/loans", response_model=schemas.LoanOut, status_code=201)
def create_loan(loan: schemas.LoanCreate, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, loan.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    emi = calculate_emi(loan.principal, loan.interest_rate, loan.tenure_months)

    # The borrower repays principal plus interest, so the balance to be
    # repaid is EMI x tenure (not just the principal).
    total_payable = round(emi * loan.tenure_months, 2)

    new_loan = models.Loan(
        customer_id=loan.customer_id,
        principal=loan.principal,
        interest_rate=loan.interest_rate,
        tenure_months=loan.tenure_months,
        emi=emi,
        total_payable=total_payable,
        outstanding_amount=total_payable,
        status="ACTIVE",
    )
    db.add(new_loan)
    db.commit()
    db.refresh(new_loan)
    return new_loan


@app.get("/loans", response_model=List[schemas.LoanOut])
def get_loans(db: Session = Depends(get_db)):
    return db.query(models.Loan).order_by(models.Loan.id).all()


@app.get("/loans/{loan_id}", response_model=schemas.LoanOut)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(models.Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


# =========================================================
# PAYMENT APIs
# =========================================================

@app.post("/loans/{loan_id}/payments")
def make_payment(loan_id: int, payment: schemas.PaymentCreate, db: Session = Depends(get_db)):
    loan = db.get(models.Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Loan is already closed")

    amount = round(payment.amount, 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment must be greater than zero")

    outstanding = round(loan.outstanding_amount, 2)
    if amount > outstanding:
        raise HTTPException(status_code=400, detail="Payment cannot exceed outstanding amount")

    loan.outstanding_amount = round(outstanding - amount, 2)
    if loan.outstanding_amount <= 0:
        loan.outstanding_amount = 0.0
        loan.status = "CLOSED"

    db.add(models.Payment(loan_id=loan.id, amount=amount))
    db.commit()
    db.refresh(loan)

    return {
        "message": "Payment successful",
        "loan_id": loan.id,
        "payment": amount,
        "remaining_amount": loan.outstanding_amount,
        "status": loan.status,
    }


@app.get("/loans/{loan_id}/payments", response_model=List[schemas.PaymentOut])
def get_payments(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(models.Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan.payments


# =========================================================
# LOAN SUMMARY
# =========================================================

@app.get("/loans/{loan_id}/summary")
def loan_summary(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(models.Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    total_paid = round(loan.total_payable - loan.outstanding_amount, 2)

    return {
        "loan_id": loan.id,
        "customer_id": loan.customer_id,
        "principal": loan.principal,
        "interest_rate": loan.interest_rate,
        "tenure_months": loan.tenure_months,
        "emi": loan.emi,
        "total_payable": loan.total_payable,
        "total_paid": total_paid,
        "outstanding_amount": loan.outstanding_amount,
        "payments_made": len(loan.payments),
        "status": loan.status,
    }
