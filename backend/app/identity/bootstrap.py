"""在受控终端为已有用户初始化首位平台管理员。"""
import argparse
from sqlalchemy import select, text
from app.core.database import SessionLocal
from app.merchant.model import User, UserPlatformRole


def bootstrap(db, user_id):
    dialect = db.get_bind().dialect.name
    lock_connection = None
    try:
        if dialect == 'mysql':
            lock_connection = db.get_bind().connect()
            if lock_connection.scalar(text("SELECT GET_LOCK('nexusops_admin_bootstrap', 10)")) != 1:
                raise RuntimeError('无法获取初始化锁')
        elif dialect == 'sqlite':
            db.execute(text('BEGIN IMMEDIATE'))
        else:
            raise RuntimeError('不支持此数据库的管理员初始化')
        if db.scalar(select(UserPlatformRole.id).where(UserPlatformRole.role == 'platform_admin').limit(1)) is not None:
            raise ValueError('平台管理员已存在')
        user = db.get(User, user_id)
        if user is None or user.status != 'active':
            raise ValueError('有效用户不存在')
        db.add_all([UserPlatformRole(user_id=user.id, role='platform_admin'), UserPlatformRole(user_id=user.id, role='super_admin')])
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if lock_connection is not None:
            try:
                lock_connection.execute(text("SELECT RELEASE_LOCK('nexusops_admin_bootstrap')"))
            finally:
                lock_connection.close()


def main():
    parser = argparse.ArgumentParser(description='为已存在的用户初始化首位平台管理员')
    parser.add_argument('user_id', type=int)
    args = parser.parse_args()
    with SessionLocal() as db:
        bootstrap(db, args.user_id)
    print('平台管理员初始化成功')

if __name__ == '__main__':
    main()
