"""允许关闭订单后重新购买，同时保留每人一笔有效订单约束。"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    bad = connection.execute(sa.text("SELECT COUNT(*) FROM voucher_orders WHERE status NOT IN ('created','paid','cancelled','expired')")).scalar_one()
    if bad:
        raise RuntimeError('存在未知订单状态，请先核查后再迁移')
    constraints = sa.inspect(connection).get_unique_constraints('voucher_orders')
    old = next((c['name'] for c in constraints if c['column_names'] == ['campaign_id', 'user_id']), None)
    if not old:
        raise RuntimeError('未找到原订单限购约束，请检查数据库结构')
    op.add_column('voucher_orders', sa.Column('active_marker', sa.Integer(), nullable=True))
    connection.execute(sa.text("UPDATE voucher_orders SET active_marker = CASE WHEN status IN ('created','paid') THEN 1 ELSE NULL END"))
    op.create_unique_constraint('uq_voucher_order_active', 'voucher_orders', ['campaign_id', 'user_id', 'active_marker'])
    op.create_check_constraint('ck_voucher_order_active', 'voucher_orders', "(status IN ('created', 'paid') AND active_marker IS NOT NULL AND active_marker = 1) OR (status IN ('cancelled', 'expired') AND active_marker IS NULL)")
    op.drop_constraint(old, 'voucher_orders', type_='unique')

def downgrade():
    connection = op.get_bind()
    duplicate = connection.execute(sa.text('SELECT 1 FROM voucher_orders GROUP BY campaign_id,user_id HAVING COUNT(*) > 1 LIMIT 1')).first()
    if duplicate:
        raise RuntimeError('存在同一活动的历史重复订单，不能安全回退')
    op.create_unique_constraint('uq_voucher_order_campaign_user', 'voucher_orders', ['campaign_id','user_id'])
    op.drop_constraint('ck_voucher_order_active', 'voucher_orders', type_='check')
    op.drop_constraint('uq_voucher_order_active', 'voucher_orders', type_='unique')
    op.drop_column('voucher_orders', 'active_marker')
