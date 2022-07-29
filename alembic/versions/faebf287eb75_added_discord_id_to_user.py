"""Added discord_id to user

Revision ID: faebf287eb75
Revises: 7c8a432e78a1
Create Date: 2022-07-28 04:16:45.525694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'faebf287eb75'
down_revision = '7c8a432e78a1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('discord_id', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('discord_id')
