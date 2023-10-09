from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

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
    print(potions_delivered)

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

    # Initial logic: bottle all barrels into red potions.

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_ml, color FROM potions"))

        p_type = {
            "red": [100,0,0,0],
            "green": [0,100,0,0],
            "blue": [0,0,100,0],
        }

        bottle_order = []

        for row in result:
            qty = row.num_ml // 100
            if qty > 0:
                bottle_order.append({
                    "potion_type": p_type[row.color],
                    "quantity": qty,
                })
        return bottle_order
