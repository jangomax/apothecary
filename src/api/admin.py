from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

from src.discord import log

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("DELETE FROM item_ledger"))
        connection.execute(sqlalchemy.text("DELETE FROM ml_ledger"))
        connection.execute(sqlalchemy.text("DELETE FROM gold_ledger"))
        connection.execute(sqlalchemy.text("DELETE FROM transactions"))
        connection.execute(sqlalchemy.text("DELETE FROM cart_item"))
        connection.execute(sqlalchemy.text("DELETE FROM carts"))

        connection.execute(sqlalchemy.text("ALTER SEQUENCE transactions_id_seq RESTART WITH 1"))
        connection.execute(sqlalchemy.text("ALTER SEQUENCE gold_ledger_id_seq RESTART WITH 1"))
        connection.execute(sqlalchemy.text("ALTER SEQUENCE ml_ledger_id_seq RESTART WITH 1"))
        connection.execute(sqlalchemy.text("ALTER SEQUENCE item_ledger_id_seq RESTART WITH 1"))
        connection.execute(sqlalchemy.text("ALTER SEQUENCE carts_n_id_seq RESTART WITH 1"))

        transaction_id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO transactions (description)
            VALUES (:desc) RETURNING id
            """), {"desc": "Init"}).scalar_one()
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger (change, transaction_id)
            VALUES (:change, :transaction_id)
            """), {"change": 100, "transaction_id": transaction_id})

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger (change_red_ml, change_green_ml, change_blue_ml, change_dark_ml, transaction_id)
            VALUES (0,0,0,0, :transaction_id)
            """
        ), {"transaction_id": transaction_id})

        catalog = connection.execute(sqlalchemy.text(
            """
            SELECT sku FROM catalog_item
            """
        ))

        for item in catalog:
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO item_ledger (sku, change, transaction_id)
                VALUES (:sku, :change, :transaction_id)
                """
            ), {"sku": item.sku, "change": 0, "transaction_id": transaction_id})


    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """

    log("Shop Info", {
        "shop_name": "Apothecary",
        "shop_owner": "Maxwell Silver",
    })

    return {
        "shop_name": "Apothecary",
        "shop_owner": "Maxwell Silver",
    }

