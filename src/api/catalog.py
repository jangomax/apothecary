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
        result = connection.execute(sqlalchemy.text("SELECT sku, name, price, potion_type, quantity FROM catalog_item WHERE quantity > 0"))
        # Can return a max of 20 items.

        catalog = []

        for item in result:
            catalog.append({
                "sku": item.sku,
                "name": item.name,
                "quantity": item.quantity,
                "price": item.price,
                "potion_type": item.potion_type
            })
        log("Current Inventory", catalog)
        return catalog