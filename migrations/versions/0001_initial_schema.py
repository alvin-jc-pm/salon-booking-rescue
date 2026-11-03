"""Initial schema, ported as it was from the prototype

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text()),
        sa.Column("price", sa.Float()),
        sa.Column("duration", sa.Integer()),
        sa.PrimaryKeyConstraint("id", name="pk_services"),
    )
    op.create_table(
        "slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Text()),
        sa.Column("available", sa.Boolean(), server_default=sa.true()),
        sa.PrimaryKeyConstraint("id", name="pk_slots"),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("service_id", sa.Integer()),
        sa.Column("slot_id", sa.Integer()),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
    )


def downgrade():
    op.drop_table("bookings")
    op.drop_table("slots")
    op.drop_table("services")
