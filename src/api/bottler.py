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

    p_type = ["red", "green", "blue"]

    with db.engine.begin() as connection:
        for item in potions_delivered:
            ml = item.quantity * 100
            qty = item.quantity
            color = p_type[item.potion_type.index(100)]

            connection.execute(sqlalchemy.text(f"UPDATE potions SET num_ml = num_ml - {ml} WHERE color = '{color}'"))
            connection.execute(sqlalchemy.text(f"UPDATE potions SET num_potions = num_potions + {qty} WHERE color = '{color}'"))

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
        num_items = connection.execute(sqlalchemy.text("SELECT sku potion_type FROM catalog_item")).rowcount
        ml_stock = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml FROM global_inventory")).first()

        ml = [ml_stock.num_red_ml, ml_stock.num_green_ml, ml_stock.num_blue_ml]

        bottle_order = {}
        p_types = {}
        cant_make = 0
        while cant_make < num_items * 2:
            items = connection.execute(sqlalchemy.text("""SELECT sku, potion_type FROM catalog_item"""))

            print(cant_make)
            for item in items:
                print(item.sku)

                p_types[item.sku] = item.potion_type

                recipe_cost = item.potion_type
                if all(recipe_cost[color] <= ml[color] for color in range(len(ml))):
                    print(f"can make {item.potion_type}")
                    if bottle_order.get(item.sku):
                        bottle_order[item.sku] += 1
                    else:
                        bottle_order[item.sku] = 1
                    ml = [ml[i] - recipe_cost[i] for i in range(len(ml))]
                    print(ml)
                else:
                    print("can't make")
                    cant_make += 1
        log("Bottle Order", bottle_order)
        return [{"potion_type": p_types[sku], "quantity": bottle_order[sku]} for sku in bottle_order.keys() if bottle_order[sku] > 0]
