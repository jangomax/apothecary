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
        for item in barrels_delivered:
            price = item.price
            qty = item.quantity
            ml = item.ml_per_barrel

            connection.execute(sqlalchemy.text(
                """
                INSERT INTO gold_ledger (change, description)
                VALUES (:change, :description)
                """),
                {
                    "change": -(qty * price),
                    "paid": qty * price,
                    "description": f"{qty}x {item.sku}"
                }
            )

            connection.execute(sqlalchemy.text(
                """
                INSERT INTO ml_ledger (change_red_ml, change_green_ml, change_blue_ml, change_dark_ml, description)
                VALUES (:change_red, :change_green, :change_blue, :change_dark, :description)
                """), 
                {
                  "change_red": ml * qty if item.potion_type[0] else 0,
                  "change_green": ml * qty if item.potion_type[1] else 0,
                  "change_blue": ml * qty if item.potion_type[2] else 0,
                  "change_dark": ml * qty if item.potion_type[3] else 0,
                  "description": f"{qty}x {item.sku}"
                }
            )

        return "OK"

# Gets called once a day
# This is where we place our order from the barrel wholesaler
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    log("Wholesale Catalog", wholesale_catalog)

    with db.engine.begin() as connection:

        sku_dict = {
            "SMALL_RED_BARREL": "num_red_ml",
            "SMALL_GREEN_BARREL": "num_green_ml",
            "SMALL_BLUE_BARREL": "num_blue_ml"
        }

        small_barrels = [item for item in wholesale_catalog if sku_dict.get(item.sku)]
        order_list = []
        gold = connection.execute(sqlalchemy.text("SELECT SUM(change) AS gold FROM gold_ledger")).scalar_one()

        ml_data = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(change_red_ml) AS num_red_ml,
            SUM(change_green_ml) AS num_green_ml,
            SUM(change_blue_ml) AS num_blue_ml
            FROM ml_ledger
            """
        )).first()
        for item in small_barrels:
            num_ml = getattr(ml_data, sku_dict[item.sku])
            print(num_ml)
            if num_ml < 100 and item.price <= gold:
                order_list.append({
                    "sku": item.sku,
                    "quantity": 1
                })
                gold -= item.price
        log("Plan", order_list)

        return order_list
