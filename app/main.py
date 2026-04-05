from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class House(Base):
    __tablename__ = "houses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    users = relationship("User", back_populates="house", cascade="all, delete")
    bills = relationship("Bill", back_populates="house", cascade="all, delete")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    house_id = Column(Integer, ForeignKey("houses.id"), nullable=False)
    house = relationship("House", back_populates="users")
    balances = relationship("Balance", back_populates="user", cascade="all, delete")

class Bill(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    house_id = Column(Integer, ForeignKey("houses.id"), nullable=False)
    house = relationship("House", back_populates="bills")
    balances = relationship("Balance", back_populates="bill", cascade="all, delete")

class Balance(Base):
    __tablename__ = "balances"
    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(Integer, ForeignKey("houses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    amount_owed = Column(Float, nullable=False)
    user = relationship("User", back_populates="balances")
    bill = relationship("Bill", back_populates="balances")

Base.metadata.create_all(bind=engine)
app = FastAPI(title="House Divided MVP")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class HouseIn(BaseModel):
    name: str

class HouseOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class UserIn(BaseModel):
    name: str
    email: EmailStr

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    house_id: int
    class Config:
        from_attributes = True

class BillIn(BaseModel):
    name: str
    total_amount: float

class BalanceOut(BaseModel):
    user_id: int
    user_name: str
    total_owed: float

@app.post("/houses", response_model=HouseOut, status_code=201)
def create_house(payload: HouseIn, db: Session = Depends(get_db)):
    house = House(name=payload.name)
    db.add(house)
    db.commit()
    db.refresh(house)
    return house

@app.post("/houses/{house_id}/users", response_model=UserOut, status_code=201)
def add_user(house_id: int, payload: UserIn, db: Session = Depends(get_db)):
    house = db.query(House).filter(House.id == house_id).one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if db.query(User).filter(User.email == payload.email).one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(name=payload.name, email=str(payload.email), house_id=house_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/houses/{house_id}/bills", status_code=201)
def add_bill(house_id: int, payload: BillIn, db: Session = Depends(get_db)):
    house = db.query(House).filter(House.id == house_id).one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    users = db.query(User).filter(User.house_id == house_id).all()
    if not users:
        raise HTTPException(status_code=400, detail="House has no users")

    bill = Bill(name=payload.name, total_amount=payload.total_amount, house_id=house_id)
    db.add(bill)
    db.commit()

    split = payload.total_amount / len(users)
    for u in users:
        bal = Balance(house_id=house_id, user_id=u.id, bill_id=bill.id, amount_owed=split)
        db.add(bal)
    db.commit()

    names = [u.name for u in users]
    return {
        "bill_id": bill.id,
        "bill_name": bill.name,
        "total_amount": bill.total_amount,
        "split_per_user": split,
        "users": names,
    }

@app.get("/houses/{house_id}/balances", response_model=list[BalanceOut])
def balances(house_id: int, db: Session = Depends(get_db)):
    house = db.query(House).filter(House.id == house_id).one_or_none()
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    users = db.query(User).filter(User.house_id == house_id).all()

    out: list[BalanceOut] = []
    for u in users:
        rows = db.query(Balance.amount_owed).filter(Balance.house_id == house_id, Balance.user_id == u.id).all()
        total = sum(r[0] for r in rows)
        out.append(BalanceOut(user_id=u.id, user_name=u.name, total_owed=total))
    return out
