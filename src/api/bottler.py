from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

from src.discord import log

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    log("Potions Delivered", potions_delivered)

    color = ["num_red_ml", "num_green_ml", "num_blue_ml"]

    with db.engine.begin() as connection:
        transaction_id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO transactions (description)
            VALUES (:desc) RETURNING id
            """
        ), {"desc": "Bottle Delivery"}).scalar_one()

        change_red = 0
        change_green = 0
        change_blue = 0
        change_dark = 0

        for item in potions_delivered:
            qty = item.quantity
            
            sku = connection.execute(sqlalchemy.text(
                """
                SELECT sku FROM catalog_item WHERE potion_type = :potion_type
                """
            ), {"potion_type": item.potion_type}).scalar_one()

            change_red += item.potion_type[0] * qty
            change_green += item.potion_type[1] * qty
            change_blue += item.potion_type[2] * qty
            change_dark += item.potion_type[3] * qty

            connection.execute(sqlalchemy.text(
                """
                INSERT INTO item_ledger (sku, change, transaction_id)
                VALUES (:sku, :change, :transaction_id)
                """
              ),
              {
                "sku": sku,
                "change": qty,
                "transaction_id": transaction_id
              }
            )
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger (change_red_ml, change_green_ml, change_blue_ml, change_dark_ml, transaction_id)
            VALUES (:change_red, :change_green, :change_blue, :change_dark, :transaction_id)
            """),
            {
                "change_red": -change_red,
                "change_green": -change_green,
                "change_blue": -change_blue,
                "change_dark": -change_dark,
                "transaction_id": transaction_id
            })

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    with db.engine.begin() as connection:
        num_potions = connection.execute(sqlalchemy.text("SELECT SUM(change) AS num_potions FROM item_ledger")).scalar_one()

        num_items = connection.execute(sqlalchemy.text("SELECT sku, potion_type FROM catalog_item")).rowcount
        ml_stock = connection.execute(sqlalchemy.text(
            """
            SELECT
            SUM(change_red_ml) AS num_red_ml,
            SUM(change_green_ml) AS num_green_ml,
            SUM(change_blue_ml) AS num_blue_ml
            FROM ml_ledger
            """
        )).first()

        sold_recently = connection.execute(sqlalchemy.text(
            """
            WITH recent AS (
              SELECT sku, transactions.id
              FROM item_ledger
              JOIN transactions ON item_ledger.transaction_id = transactions.id
              WHERE change < 0
              ORDER BY transactions.id DESC
              LIMIT 6
            )
            SELECT DISTINCT sku FROM recent
            """
        ))

        sku_list = [row.sku for row in sold_recently.fetchall()]
        print(sku_list)

        ml = [ml_stock.num_red_ml, ml_stock.num_green_ml, ml_stock.num_blue_ml]
        print(ml)

        p_types = {}
        bottle_order = {}
        cant_make = 0
        while cant_make < num_items * 2 and num_potions < 295:
            print(cant_make)
            for sku in sku_list:
                if sku == 'BG_POTION_0' or sku == 'BLUE_POTION_0':
                    continue
                potion_type = connection.execute(sqlalchemy.text(
                    """
                    SELECT potion_type FROM catalog_item
                    WHERE sku = :sku
                    """), {"sku": sku}).scalar_one()
                print(sku)

                p_types[sku] = potion_type
                recipe_cost = potion_type
                if all(recipe_cost[color] <= ml[color] for color in range(len(ml))):
                    print(f"can make {potion_type}")

                    bottle_order[sku] = 1 + bottle_order.get(sku, 0)
                    num_potions += 1
                    ml = [ml[i] - recipe_cost[i] for i in range(len(ml))]
                    cant_make //= 2
                    print(ml)
                else:
                    print("can't make")
                    cant_make += 1
        log("Bottle Order", bottle_order)
        return [{"potion_type": p_types[sku], "quantity": bottle_order[sku]} for sku in bottle_order.keys() if bottle_order[sku] > 0]
