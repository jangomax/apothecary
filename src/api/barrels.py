from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

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
    print(barrels_delivered)

    with db.engine.begin() as connection:
        price = barrels_delivered[0].price
        qty = barrels_delivered[0].quantity
        ml = barrels_delivered[0].ml_per_barrel

        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = gold - {qty * price}"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = num_red_ml + {qty * ml}"))

        return "OK"

# Gets called once a day
# This is where we place our order from the barrel wholesaler
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:

        sku_dict = {
            "SMALL_RED_BARREL": "red",
            "SMALL_GREEN_BARREL": "green",
            "SMALL_BLUE_BARREL": "blue"
        }

        small_barrels = [item for item in wholesale_catalog if sku_dict.get(item.sku)]
        order_list = []
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).first().gold

        for item in small_barrels:
            result = connection.execute(sqlalchemy.text(f"SELECT num_potions FROM potions WHERE color = {sku_dict[item.name]}"))
            num_potions = result.first()
            if num_potions < 10 and item.price <= gold:
                order_list.append({
                    "sku": item.name,
                    "quantity": 1
                })
                gold -= item.price

        return order_list
