"""added user.last_points_checked

Revision ID: caf4cb79379b
Revises: faebf287eb75
Create Date: 2022-07-31 03:23:34.782724

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
from database import engine

revision = 'caf4cb79379b'
down_revision = 'faebf287eb75'
branch_labels = None
depends_on = None


def upgrade():
    columns = Inspector.from_engine(engine).get_columns('user')
    for column in columns:
        if column['name'] == 'last_worth_checked':
            return

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_worth_checked', sa.Integer(), nullable=True))
    op.execute("UPDATE user SET last_points_checked = 0")


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('last_points_checked')
