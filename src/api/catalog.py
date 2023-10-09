from fastapi import APIRouter

import sqlalchemy
from src import database as db

from src.discord import log

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT color, num_potions FROM potions"))
        # Can return a max of 20 items.

        p_type = {
            "red": [100,0,0,0],
            "green": [0,100,0,0],
            "blue": [0,0,100,0],
        }

        catalog = []

        for row in result:
            if row.num_potions > 0:
                catalog.append({
                    "sku": row.color + "_POTION_0",
                    "name": row.color + " potion",
                    "quantity": row.num_potions,
                    "price": 50,
                    "potion_type": p_type[row.color]
                })
        log("Current Inventory", catalog)
        return catalog