"""向明确指定的本地开发库一次性添加商户与商品。"""
import os
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import SessionLocal
from app.merchant.model import Merchant, Product, ProductCategory, ProductSku, Inventory

SHOPS = [
    ('巷口小厨', 'dining', '招牌菜', [('番茄牛腩饭', '28.00'), ('香菇鸡腿饭', '24.00'), ('时蔬拼盘', '16.00')]),
    ('山茶咖啡', 'drinks', '饮品', [('拿铁咖啡', '22.00'), ('茉莉奶茶', '18.00'), ('柠檬气泡水', '15.00')]),
    ('暖麦烘焙', 'bakery', '烘焙', [('原味可颂', '12.00'), ('全麦吐司', '18.00'), ('草莓蛋糕', '26.00')]),
    ('邻里便利店', 'supermarket', '日用品', [('纯净水', '3.00'), ('抽纸', '12.00'), ('燕麦饼干', '10.00')]),
    ('青禾果蔬', 'fresh', '水果蔬菜', [('苹果', '9.80'), ('香蕉', '6.80'), ('新鲜西红柿', '7.80')]),
    ('光点数码', 'electronics', '数码配件', [('充电线', '29.00'), ('无线鼠标', '59.00'), ('手机支架', '19.00')]),
    ('花间个护', 'beauty', '洗护用品', [('洗手液', '18.00'), ('护手霜', '25.00'), ('洗发水', '39.00')]),
    ('墨香文具', 'books', '文具', [('笔记本', '15.00'), ('中性笔', '5.00'), ('文件夹', '8.00')]),
]
def main():
    url = make_url(settings.database_url)
    if os.environ.get('NEXUSOPS_ENV') != 'dev' or url.host not in ('127.0.0.1', 'localhost') or url.database != 'nexusops':
        raise SystemExit('仅允许在显式指定的本机 nexusops 开发库中运行')
    with SessionLocal.begin() as db:
        names = [row[0] for row in SHOPS]
        if db.scalar(select(Merchant.id).where(Merchant.name.in_(names)).limit(1)) is not None:
            raise SystemExit('商户名称已存在，未写入任何数据')
        for name, category, product_group, products in SHOPS:
            merchant = Merchant(name=name, category=category, description='', status='active')
            db.add(merchant); db.flush()
            group = ProductCategory(merchant_id=merchant.id, name=product_group, sort_order=0, status='active')
            db.add(group); db.flush()
            for product_name, price in products:
                product = Product(merchant_id=merchant.id, category_id=group.id, name=product_name, status='active')
                product.skus.append(ProductSku(name='默认规格', price=Decimal(price), status='active', inventory=Inventory(available=50)))
                db.add(product)
    print(f'已新增 {len(SHOPS)} 家商户、{len(SHOPS)} 个商品分类和 {sum(len(row[3]) for row in SHOPS)} 件商品。')

if __name__ == '__main__':
    main()
