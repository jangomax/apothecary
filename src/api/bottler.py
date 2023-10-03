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

    with db.engine.begin() as connection:
        ml = potions_delivered[0].quantity * 100
        qty = potions_delivered[0].quantity

        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_red_potions FROM global_inventory"))
        row = result.first()

        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = {row.num_red_ml - ml}"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_potions = {row.num_red_potions + qty}"))

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
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory"))
        first_row = result.first()

        qty = first_row.num_red_ml // 100

        if qty == 0:
            return []
        return [
                {
                    "potion_type": [100, 0, 0, 0],
                    "quantity": qty,
                }
            ]
