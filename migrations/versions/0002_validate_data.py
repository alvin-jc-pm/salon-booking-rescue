"""Real types and rules: prices in cents, real timestamps, foreign keys

Revision ID: 0002
Revises: 0001

Existing rows are converted, not dropped. If a row cannot be converted
(a start_time that is not a date, a booking for a service that does not
exist), the migration stops with an error so the bad data can be fixed
by hand. Start times without a UTC offset are read as UTC.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("services", sa.Column("price_cents", sa.Integer()))
    op.execute("UPDATE services SET price_cents = CAST(ROUND(price * 100) AS INTEGER)")
    with op.batch_alter_table("services") as batch:
        batch.drop_column("price")
        batch.alter_column("name", existing_type=sa.Text(), type_=sa.String(100), nullable=False)
        batch.alter_column("price_cents", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("duration", existing_type=sa.Integer(), nullable=False)
        batch.create_check_constraint(op.f("ck_services_price_cents_positive"), "price_cents > 0")
        batch.create_check_constraint(op.f("ck_services_duration_positive"), "duration > 0")

    with op.batch_alter_table("slots") as batch:
        batch.alter_column(
            "start_time",
            existing_type=sa.Text(),
            type_=sa.DateTime(timezone=True),
            nullable=False,
            postgresql_using="start_time::timestamptz",
        )

    with op.batch_alter_table("bookings") as batch:
        batch.alter_column("customer_name", existing_type=sa.Text(), type_=sa.String(100), nullable=False)
        batch.alter_column("phone", existing_type=sa.Text(), type_=sa.String(20), nullable=False)
        batch.alter_column("service_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("slot_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(op.f("fk_bookings_service_id_services"), "services", ["service_id"], ["id"])
        batch.create_foreign_key(op.f("fk_bookings_slot_id_slots"), "slots", ["slot_id"], ["id"])


def downgrade():
    with op.batch_alter_table("bookings") as batch:
        batch.drop_constraint(op.f("fk_bookings_slot_id_slots"), type_="foreignkey")
        batch.drop_constraint(op.f("fk_bookings_service_id_services"), type_="foreignkey")
        batch.alter_column("slot_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("service_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("phone", existing_type=sa.String(20), type_=sa.Text(), nullable=True)
        batch.alter_column("customer_name", existing_type=sa.String(100), type_=sa.Text(), nullable=True)

    with op.batch_alter_table("slots") as batch:
        batch.alter_column(
            "start_time",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.Text(),
            nullable=True,
            postgresql_using="start_time::text",
        )

    op.add_column("services", sa.Column("price", sa.Float()))
    op.execute("UPDATE services SET price = price_cents / 100.0")
    with op.batch_alter_table("services") as batch:
        batch.drop_constraint(op.f("ck_services_duration_positive"), type_="check")
        batch.drop_constraint(op.f("ck_services_price_cents_positive"), type_="check")
        batch.drop_column("price_cents")
        batch.alter_column("duration", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("name", existing_type=sa.String(100), type_=sa.Text(), nullable=True)
