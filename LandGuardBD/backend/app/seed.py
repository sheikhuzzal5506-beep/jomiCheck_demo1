from sqlalchemy import select

from .database import Base, engine, SessionLocal
from .models import User, RegistryOffice, Person, LandParcel, Deed, MutationRecord
from .security import hash_password


def seed():
    """Create the complete synthetic dataset without duplicating existing rows."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.scalar(select(User).where(User.username == "admin")):
            db.add(User(username="admin", password_hash=hash_password("LandGuard123!"), role="System Administrator"))

        office = db.scalar(select(RegistryOffice).where(RegistryOffice.name_en == "Dhaka Demo Sub-Registry Office"))
        if not office:
            office = RegistryOffice(
                name_en="Dhaka Demo Sub-Registry Office",
                name_bn="Dhaka Demo Sub-Registry Office",
                district="Dhaka",
            )
            db.add(office)
            db.flush()

        people = []
        for i in range(1, 51):
            person = db.scalar(select(Person).where(Person.person_ref == f"DEMO-P-{i:03d}"))
            if not person:
                person = Person(
                    person_ref=f"DEMO-P-{i:03d}",
                    name_en=f"Demo Person {i:02d}",
                    name_bn=f"Demo Person {i:02d}",
                )
                db.add(person)
            people.append(person)
        db.flush()

        for i in range(1, 26):
            deed_number = f"DEMO-2024-{i:03d}"
            deed = db.scalar(select(Deed).where(Deed.deed_number == deed_number))
            if not deed:
                parcel = db.scalar(select(LandParcel).where(LandParcel.khatian_number == f"K-{2000 + i}"))
                if not parcel:
                    parcel = LandParcel(
                        mouza=f"Demo Mouza {((i - 1) % 5) + 1}",
                        jl_number=f"JL-{100 + i % 7}",
                        khatian_number=f"K-{2000 + i}",
                        dag_number=f"D-{300 + i}",
                        area_decimal=round(2.5 + i * 0.37, 2),
                        demo_label="DEMO",
                    )
                    db.add(parcel)
                    db.flush()
                deed = Deed(
                    deed_number=deed_number,
                    registration_date=f"2024-{((i - 1) % 12) + 1:02d}-{((i - 1) % 27) + 1:02d}",
                    registration_year=2024,
                    office_id=office.id,
                    parcel_id=parcel.id,
                    seller_id=people[(i - 1) * 2].id,
                    buyer_id=people[(i - 1) * 2 + 1].id,
                    deed_type="Sale",
                    status="DEMO_RECORDED",
                )
                db.add(deed)
                db.flush()

            if i % 2 == 0 and not db.scalar(select(MutationRecord).where(MutationRecord.deed_id == deed.id)):
                db.add(MutationRecord(deed_id=deed.id, mutation_ref=f"MUT-DEMO-{i:04d}", status="DEMO_APPROVED"))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
