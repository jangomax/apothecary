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
        result = connection.execute(sqlalchemy.text(
            """
            SELECT catalog_item.sku, name, price, potion_type, SUM(change) AS quantity
            FROM catalog_item
            JOIN item_ledger ON catalog_item.sku = item_ledger.sku
            GROUP BY catalog_item.sku, name, price, potion_type
            """
        ))

        catalog = []

        for item in result:
            if item.quantity > 0:
                catalog.append({
                    "sku": item.sku,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "potion_type": item.potion_type
                })
        log("Current Inventory", catalog)
        return catalog