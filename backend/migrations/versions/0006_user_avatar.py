"""保存用户头像。"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('avatar', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('users', 'avatar')
