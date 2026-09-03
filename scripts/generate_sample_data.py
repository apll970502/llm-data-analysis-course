"""가상 쇼핑몰 샘플 데이터 생성 스크립트.

프로젝트 루트에서 실행합니다.
    python scripts/generate_sample_data.py

실행하면 data/raw/ 아래에 다음 파일이 생성됩니다.
    customers.csv, products.csv, orders.csv, order_items.csv
"""

import random
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("ko_KR")
random.seed(42)
Faker.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

NUM_CUSTOMERS = 200
NUM_PRODUCTS = 50
NUM_ORDERS = 500

CATEGORIES = ["의류", "전자기기", "식품", "도서", "생활용품", "뷰티", "스포츠"]


def generate_customers():
    rows = []
    for customer_id in range(1, NUM_CUSTOMERS + 1):
        rows.append(
            {
                "customer_id": customer_id,
                "name": fake.name(),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "address": fake.address(),
                "join_date": fake.date_between(start_date="-2y", end_date="today"),
            }
        )
    return pd.DataFrame(rows)


def generate_products():
    rows = []
    for product_id in range(1, NUM_PRODUCTS + 1):
        rows.append(
            {
                "product_id": product_id,
                "name": fake.word() + " " + random.choice(["세트", "패키지", "기본형", "프리미엄"]),
                "category": random.choice(CATEGORIES),
                "price": random.randrange(3000, 200000, 1000),
                "stock": random.randint(0, 300),
            }
        )
    return pd.DataFrame(rows)


def generate_orders():
    rows = []
    for order_id in range(1, NUM_ORDERS + 1):
        rows.append(
            {
                "order_id": order_id,
                "customer_id": random.randint(1, NUM_CUSTOMERS),
                "order_date": fake.date_between(start_date="-1y", end_date="today"),
                "status": random.choice(["결제완료", "배송중", "배송완료", "취소"]),
            }
        )
    return pd.DataFrame(rows)


def generate_order_items(orders_df):
    rows = []
    order_item_id = 1
    for order_id in orders_df["order_id"]:
        num_items = random.randint(1, 4)
        for _ in range(num_items):
            product_id = random.randint(1, NUM_PRODUCTS)
            quantity = random.randint(1, 3)
            rows.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": order_id,
                    "product_id": product_id,
                    "quantity": quantity,
                }
            )
            order_item_id += 1
    return pd.DataFrame(rows)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    customers_df = generate_customers()
    products_df = generate_products()
    orders_df = generate_orders()
    order_items_df = generate_order_items(orders_df)

    customers_df.to_csv(RAW_DIR / "customers.csv", index=False, encoding="utf-8-sig")
    products_df.to_csv(RAW_DIR / "products.csv", index=False, encoding="utf-8-sig")
    orders_df.to_csv(RAW_DIR / "orders.csv", index=False, encoding="utf-8-sig")
    order_items_df.to_csv(RAW_DIR / "order_items.csv", index=False, encoding="utf-8-sig")

    print(f"완료: {RAW_DIR} 에 4개 파일을 생성했습니다.")
    print(f"- customers.csv   ({len(customers_df)}행)")
    print(f"- products.csv    ({len(products_df)}행)")
    print(f"- orders.csv      ({len(orders_df)}행)")
    print(f"- order_items.csv ({len(order_items_df)}행)")


if __name__ == "__main__":
    main()
