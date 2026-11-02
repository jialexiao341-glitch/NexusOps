"""允许管理员创建手机号尚未验证的用户。"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('users') as batch:
        batch.alter_column('mobile_verified_at', existing_type=sa.DateTime(), nullable=True)

def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text('SELECT COUNT(*) FROM users WHERE mobile_verified_at IS NULL')).scalar_one():
        raise RuntimeError('存在手机号未验证的用户，无法回退此迁移')
    with op.batch_alter_table('users') as batch:
        batch.alter_column('mobile_verified_at', existing_type=sa.DateTime(), nullable=False)
