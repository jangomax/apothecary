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
            type = sku_dict[item.sku]

            connection.execute(sqlalchemy.text(f" UPDATE global_inventory SET gold = gold - :paid, {type} = {type} + :amt"), 
                {
                    "amt": qty * ml,
                    "paid": qty * price
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
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()

        shop_data = connection.execute(sqlalchemy.text("""SELECT * FROM global_inventory""")).first()
        for item in small_barrels:
            num_ml = getattr(shop_data, sku_dict[item.sku])
            print(num_ml)
            if num_ml < 100 and item.price <= gold:
                order_list.append({
                    "sku": item.sku,
                    "quantity": 1
                })
                gold -= item.price
        log("Plan", order_list)

        return order_list
