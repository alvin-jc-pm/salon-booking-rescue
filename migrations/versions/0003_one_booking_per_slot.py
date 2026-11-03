"""One booking per slot, enforced by the database

Revision ID: 0003
Revises: 0002

Adds a UNIQUE rule on bookings.slot_id, so two bookings for the same
slot cannot both be saved, even when two requests arrive at once.

Drops slots.available. Whether a slot is free now comes from whether a
booking exists for it, so the two can never disagree. (The prototype
never set it back when a booking was deleted.)

If the database already holds double bookings, this migration stops
with an error. Decide which booking to keep, delete the other, and run
it again.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("bookings") as batch:
        batch.create_unique_constraint(op.f("uq_bookings_slot_id"), ["slot_id"])
    with op.batch_alter_table("slots") as batch:
        batch.drop_column("available")


def downgrade():
    op.add_column("slots", sa.Column("available", sa.Boolean(), server_default=sa.true()))
    op.execute(
        "UPDATE slots SET available = NOT EXISTS (SELECT 1 FROM bookings WHERE bookings.slot_id = slots.id)"
    )
    with op.batch_alter_table("bookings") as batch:
        batch.drop_constraint(op.f("uq_bookings_slot_id"), type_="unique")
