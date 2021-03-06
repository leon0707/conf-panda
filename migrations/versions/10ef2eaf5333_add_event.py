"""add event

Revision ID: 10ef2eaf5333
Revises: 3379af231506
Create Date: 2016-12-13 19:20:34.437955

"""

# revision identifiers, used by Alembic.
revision = '10ef2eaf5333'
down_revision = '3379af231506'

from alembic import op
import sqlalchemy as sa
from app.utils.customDataType import NestedMutableJson as JsonObject


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('event_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('conference_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('event', JsonObject, nullable=True),
    sa.ForeignKeyConstraint(['conference_id'], ['conferences.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('event_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_event_logs_timestamp'), ['timestamp'], unique=False)

    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('event_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_event_logs_timestamp'))

    op.drop_table('event_logs')
    ### end Alembic commands ###
