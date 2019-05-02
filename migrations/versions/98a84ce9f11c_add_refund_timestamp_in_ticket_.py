"""add refund_timestamp in ticket transaction

Revision ID: 98a84ce9f11c
Revises: 359785c37503
Create Date: 2018-07-22 19:08:58.379852

"""

# revision identifiers, used by Alembic.
revision = '98a84ce9f11c'
down_revision = '359785c37503'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ticket_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('refund_timestamp', sa.DateTime(), nullable=True))

    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ticket_transactions', schema=None) as batch_op:
        batch_op.drop_column('refund_timestamp')

    ### end Alembic commands ###
