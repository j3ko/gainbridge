"""replace overwrite_existing with write_mode

Revision ID: d9d4783a4222
Revises: aa49782b4b7f
Create Date: 2026-08-25 15:51:49.327481

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'd9d4783a4222'
down_revision = 'aa49782b4b7f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("job") as batch_op:
        batch_op.add_column(
            sa.Column(
                "write_mode",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="fix",
            )
        )

    op.execute(
        "UPDATE job SET write_mode = 'overwrite' WHERE overwrite_existing = 1"
    )
    op.execute("UPDATE job SET write_mode = 'fix' WHERE overwrite_existing = 0")

    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_column("overwrite_existing")


def downgrade():
    with op.batch_alter_table("job") as batch_op:
        batch_op.add_column(
            sa.Column(
                "overwrite_existing",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    op.execute(
        "UPDATE job SET overwrite_existing = 1 WHERE write_mode = 'overwrite'"
    )
    op.execute(
        "UPDATE job SET overwrite_existing = 0 WHERE write_mode IN ('fix', 'skip')"
    )

    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_column("write_mode")
