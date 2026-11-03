"""商户经营类别；商品分类由各商户单独维护。"""
from enum import StrEnum

class MerchantCategory(StrEnum):
    DINING = 'dining'
    RETAIL = 'retail'
    SERVICES = 'services'
    DRINKS = 'drinks'
    BAKERY = 'bakery'
    SUPERMARKET = 'supermarket'
    FRESH = 'fresh'
    ELECTRONICS = 'electronics'
    BEAUTY = 'beauty'
    BOOKS = 'books'
    ENTERTAINMENT = 'entertainment'
    OTHER = 'other'

MERCHANT_CATEGORY_LABELS = {
    MerchantCategory.DINING: '餐饮',
    MerchantCategory.RETAIL: '零售',
    MerchantCategory.SERVICES: '生活服务',
    MerchantCategory.DRINKS: '茶饮咖啡',
    MerchantCategory.BAKERY: '烘焙甜品',
    MerchantCategory.SUPERMARKET: '超市便利',
    MerchantCategory.FRESH: '生鲜果蔬',
    MerchantCategory.ELECTRONICS: '数码家电',
    MerchantCategory.BEAUTY: '美妆个护',
    MerchantCategory.BOOKS: '图书文具',
    MerchantCategory.ENTERTAINMENT: '休闲娱乐',
    MerchantCategory.OTHER: '其他',
}
