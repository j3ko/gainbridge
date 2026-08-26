"""drop source schedule_enabled

Revision ID: f3a1c9e6b7d2
Revises: 808c3ff059c7
Create Date: 2026-08-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a1c9e6b7d2'
down_revision = '808c3ff059c7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE source SET schedule_cron = NULL WHERE schedule_enabled = 0")
    with op.batch_alter_table("source") as batch_op:
        batch_op.drop_column("schedule_enabled")


def downgrade():
    with op.batch_alter_table("source") as batch_op:
        batch_op.add_column(
            sa.Column(
                "schedule_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    op.execute(
        "UPDATE source SET schedule_enabled = 1 WHERE schedule_cron IS NOT NULL"
    )
