"""Removed Rich field

Revision ID: a583f3f0b466
Revises: c1dc420b67d4
Create Date: 2020-09-03 12:54:06.147712

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a583f3f0b466'
down_revision = 'c1dc420b67d4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.drop_column('rich')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rich', sa.BOOLEAN(), nullable=True))

    # ### end Alembic commands ###
