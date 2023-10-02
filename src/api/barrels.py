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
        result = connection.execute(sqlalchemy.text("SELECT gold, num_red_ml FROM global_inventory"))
        row = result.first()

        price = barrels_delivered[0].price
        qty = barrels_delivered[0].quantity
        ml = barrels_delivered[0].ml_per_barrel

        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {row.gold - (qty * price)}"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = {row.num_red_ml + (qty * ml)}"))

        return "OK"

# Gets called once a day
# This is where we place our order from the barrel wholesaler
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, gold FROM global_inventory"))
        first_row = result.first()

        qty = 0

        red_barrels = [item for item in wholesale_catalog if item.sku == "SMALL_RED_BARREL" and item.quantity > 0]

        if (
            first_row.num_red_potions < 10 and 
            first_row.gold > wholesale_catalog[0].price and
            red_barrels[0].quantity > 0
        ):
            qty = 1

        

        return [
            {
                "sku": "SMALL_RED_BARREL",
                "quantity": qty
            }
        ]
