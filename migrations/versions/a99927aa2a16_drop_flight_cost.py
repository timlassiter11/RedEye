"""drop flight cost

Revision ID: a99927aa2a16
Revises: ee6d298ccdd9
Create Date: 2022-06-26 19:31:13.164840

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a99927aa2a16'
down_revision = 'ee6d298ccdd9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('flight', 'cost')
    op.drop_column('flight', 'arrival_time')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('flight', sa.Column('arrival_time', mysql.TIME(), nullable=False))
    op.add_column('flight', sa.Column('cost', mysql.FLOAT(), nullable=False))
    # ### end Alembic commands ###
