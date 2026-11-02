"""区分不可修改的登录账号与可修改的昵称。"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    """检查历史数据，再要求账号与密码哈希必填并增加昵称。"""
    connection = op.get_bind()
    missing = connection.execute(sa.text("SELECT COUNT(*) FROM users WHERE username IS NULL OR password_hash IS NULL")).scalar_one()
    if missing:
        raise RuntimeError("存在未设置账号或密码的用户，请先通过受控流程处理后再迁移")
    op.add_column("users", sa.Column("nickname", sa.String(80), nullable=True))
    op.alter_column("users", "username", existing_type=sa.String(64), nullable=False)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)

def downgrade():
    """恢复账号、密码字段可空并删除昵称字段。"""
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "username", existing_type=sa.String(64), nullable=True)
    op.drop_column("users", "nickname")
