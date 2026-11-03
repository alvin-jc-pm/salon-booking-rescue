from sqlalchemy import Boolean, Float, Integer, MetaData, Text, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable constraint names, so later migrations can find and change them.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Float)
    duration: Mapped[int | None] = mapped_column(Integer)


class Slot(Base):
    __tablename__ = "slots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[str | None] = mapped_column(Text)
    available: Mapped[bool | None] = mapped_column(Boolean, server_default=true())


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    service_id: Mapped[int | None] = mapped_column(Integer)
    slot_id: Mapped[int | None] = mapped_column(Integer)
