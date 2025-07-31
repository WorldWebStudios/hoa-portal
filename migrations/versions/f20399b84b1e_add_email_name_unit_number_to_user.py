"""Add email, name, unit_number to User

Revision ID: f20399b84b1e
Revises: c8e665e5a12f
Create Date: 2025-07-29 18:56:23.694352

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f20399b84b1e'
down_revision = 'c8e665e5a12f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('unit_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('role', sa.String(length=50), nullable=True))
        batch_op.create_unique_constraint('uq_user_email', ['email'])

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_email', type_='unique')
        batch_op.drop_column('role')
        batch_op.drop_column('unit_number')
        batch_op.drop_column('name')
        batch_op.drop_column('email')

    # ### end Alembic commands ###
