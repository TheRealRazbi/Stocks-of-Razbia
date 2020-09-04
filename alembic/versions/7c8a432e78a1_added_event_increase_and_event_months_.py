"""Added event_increase and event_months_remaining

Revision ID: 7c8a432e78a1
Revises: a583f3f0b466
Create Date: 2020-09-03 14:28:20.583004

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c8a432e78a1'
down_revision = 'a583f3f0b466'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.add_column(sa.Column('event_increase', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('event_months_remaining', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.drop_column('event_months_remaining')
        batch_op.drop_column('event_increase')

    # ### end Alembic commands ###
