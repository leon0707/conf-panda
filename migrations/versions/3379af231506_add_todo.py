"""add Todo

Revision ID: 3379af231506
Revises: a9758ba3a4db
Create Date: 2016-12-05 13:46:29.858455

"""

# revision identifiers, used by Alembic.
revision = '3379af231506'
down_revision = 'a9758ba3a4db'

from alembic import op
import sqlalchemy as sa
from app.utils.customDataType import NestedMutableJson as JsonObject

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('todos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conference_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('list', JsonObject, nullable=True),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['conference_id'], ['conferences.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('todos')
    ### end Alembic commands ###