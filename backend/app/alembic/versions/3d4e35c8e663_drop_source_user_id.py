"""drop source user_id

Revision ID: 3d4e35c8e663
Revises: f3a1c9e6b7d2
Create Date: 2026-08-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '3d4e35c8e663'
down_revision = 'f3a1c9e6b7d2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("source") as batch_op:
        batch_op.drop_column("user_id")


def downgrade():
    with op.batch_alter_table("source") as batch_op:
        batch_op.add_column(
            sa.Column(
                "user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
