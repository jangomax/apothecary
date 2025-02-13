from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

from src.discord import log

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

# We receive receipt of our purchase and have to put it in our own records
@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    log("Barrels Delivered", barrels_delivered)

    sku_dict = {
        "SMALL_RED_BARREL": "num_red_ml",
        "SMALL_GREEN_BARREL": "num_green_ml",
        "SMALL_BLUE_BARREL": "num_blue_ml"
    }

    with db.engine.begin() as connection:

        transaction_id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO transactions (description)
            VALUES (:desc)
            RETURNING id
            """
        ), {"desc": "Barrel Purchase"}).scalar_one()

        total_price = 0
        change_red = 0
        change_green = 0
        change_blue = 0
        change_dark = 0
        
        for item in barrels_delivered:
            price = item.price
            qty = item.quantity
            ml = item.ml_per_barrel

            total_price += (qty * price)

            change_red += ml * qty if item.potion_type[0] else 0
            change_green += ml * qty if item.potion_type[1] else 0
            change_blue += ml * qty if item.potion_type[2] else 0
            change_dark += ml * qty if item.potion_type[3] else 0

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger (change_red_ml, change_green_ml, change_blue_ml, change_dark_ml, transaction_id)
            VALUES (:change_red, :change_green, :change_blue, :change_dark, :transaction_id)
            """),
            {
                "change_red": change_red,
                "change_green": change_green,
                "change_blue": change_blue,
                "change_dark": change_dark,
                "transaction_id": transaction_id
            }
        )

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger (change, transaction_id)
            VALUES (:change, :transaction_id)
            """),
            {
                "change": -(total_price),
                "transaction_id": transaction_id
            })

        return "OK"

# Gets called once a day
# This is where we place our order from the barrel wholesaler
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    log("Wholesale Catalog", wholesale_catalog)
    return []

    with db.engine.begin() as connection:

        small_dict = {
            "SMALL_RED_BARREL": "num_red_ml",
            "SMALL_GREEN_BARREL": "num_green_ml",
            "SMALL_BLUE_BARREL": "num_blue_ml"
        }
        medium_dict = {
            "MEDIUM_RED_BARREL": "num_red_ml",
            "MEDIUM_GREEN_BARREL": "num_green_ml",
            "MEDIUM_BLUE_BARREL": "num_blue_ml"
        }

        small_barrels = [item for item in wholesale_catalog if small_dict.get(item.sku)]
        medium_barrels = [item for item in wholesale_catalog if medium_dict.get(item.sku)]
        order_dict = {}

        gold = connection.execute(sqlalchemy.text("SELECT SUM(change) AS gold FROM gold_ledger")).scalar_one()
        initialGold = gold

        ml_data = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(change_red_ml) AS num_red_ml,
            SUM(change_green_ml) AS num_green_ml,
            SUM(change_blue_ml) AS num_blue_ml
            FROM ml_ledger
            """
        )).first()
        total_ml = ml_data.num_red_ml + ml_data.num_green_ml + ml_data.num_blue_ml
        limit = 0
        if total_ml > 80000:
            log("Plan", {"Barreling":"Too much ml"})
            return []
        if len(medium_barrels) == 0:
            while gold > initialGold // 2 and limit < 9:
                limit += 1
                for item in small_barrels:
                    num_ml = getattr(ml_data, small_dict[item.sku])
                    print(num_ml)
                    if num_ml < 1000 and item.price <= gold:
                        order_dict[item.sku] = 1 + order_dict.get(item.sku, 0)
                        gold -= item.price
        else:
            for item in small_barrels:
                num_ml = getattr(ml_data, small_dict[item.sku])
                print(num_ml)
                if num_ml < 1000 and item.price <= gold:
                    order_dict[item.sku] = 1 + order_dict.get(item.sku, 0)
                    gold -= item.price
        limit = 0
        while gold > initialGold // 2 and limit < 9:
            limit += 1
            for item in medium_barrels:
                num_ml = getattr(ml_data, medium_dict[item.sku])
                print(num_ml)
                if num_ml < 2000 and item.price <= gold:
                    order_dict[item.sku] = 1 + order_dict.get(item.sku, 0)
                    gold -= item.price
        log("Plan", order_dict)

        return [{"sku": k, "quantity": order_dict[k]} for k in order_dict]
