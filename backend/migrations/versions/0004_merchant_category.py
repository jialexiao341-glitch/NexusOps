"""给商户增加可选的经营类别，不修改现有商户数据。"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('merchants', sa.Column('category', sa.String(length=30), nullable=True))

def downgrade():
    op.drop_column('merchants', 'category')
