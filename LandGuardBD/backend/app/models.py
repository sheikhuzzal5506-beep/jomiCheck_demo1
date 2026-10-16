from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def now_utc(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="Registry Officer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class RegistryOffice(Base):
    __tablename__ = "registry_offices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_en: Mapped[str] = mapped_column(String(180))
    name_bn: Mapped[str] = mapped_column(String(180))
    district: Mapped[str] = mapped_column(String(100), default="Dhaka")

class Person(Base):
    __tablename__ = "persons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_ref: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(160))
    name_bn: Mapped[str] = mapped_column(String(160), default="ডেমো ব্যক্তি")

class LandParcel(Base):
    __tablename__ = "land_parcels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mouza: Mapped[str] = mapped_column(String(120), index=True)
    jl_number: Mapped[str] = mapped_column(String(30))
    khatian_number: Mapped[str] = mapped_column(String(40), index=True)
    dag_number: Mapped[str] = mapped_column(String(40), index=True)
    area_decimal: Mapped[float] = mapped_column(Float)
    demo_label: Mapped[str] = mapped_column(String(20), default="DEMO")

class Deed(Base):
    __tablename__ = "deeds"
    __table_args__ = (UniqueConstraint("deed_number", "registration_year", name="uq_deed_year"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deed_number: Mapped[str] = mapped_column(String(50), index=True)
    registration_date: Mapped[str] = mapped_column(String(20))
    registration_year: Mapped[int] = mapped_column(Integer, index=True)
    office_id: Mapped[int] = mapped_column(ForeignKey("registry_offices.id"))
    parcel_id: Mapped[int] = mapped_column(ForeignKey("land_parcels.id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    buyer_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    deed_type: Mapped[str] = mapped_column(String(50), default="Sale")
    status: Mapped[str] = mapped_column(String(30), default="DEMO_RECORDED")
    office: Mapped[RegistryOffice] = relationship()
    parcel: Mapped[LandParcel] = relationship()
    seller: Mapped[Person] = relationship(foreign_keys=[seller_id])
    buyer: Mapped[Person] = relationship(foreign_keys=[buyer_id])

class MutationRecord(Base):
    __tablename__ = "mutation_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deed_id: Mapped[int] = mapped_column(ForeignKey("deeds.id"))
    mutation_ref: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="DEMO_APPROVED")
    note: Mapped[str] = mapped_column(Text, default="Synthetic demonstration record")
    deed: Mapped[Deed] = relationship()

class VerificationJob(Base):
    __tablename__ = "verification_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), index=True)
    deed_number: Mapped[str] = mapped_column(String(50), default="")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(80), default="demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class DocumentHashReference(Base):
    __tablename__ = "document_hash_references"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deed_id: Mapped[int] = mapped_column(ForeignKey("deeds.id"), unique=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    note: Mapped[str] = mapped_column(String(255), default="Synthetic test hash only")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(80), default="demo")
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
