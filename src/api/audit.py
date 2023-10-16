from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

import sqlalchemy
from src import database as db

from src.discord import log

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT gold, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory")).first()
        potions = connection.execute(sqlalchemy.text("SELECT qty FROM catalog_item WHERE qty > 0"))

        gold = inv.gold
        total_ml = inv.num_red_ml + inv.num_green_ml + inv.num_blue_ml + inv.num_dark_ml
        total_potions = 0

        for potion in potions:
            total_potions += potion.qty

        log("Audit", {
            "number_of_potions": total_potions, 
            "ml_in_barrels": total_ml,
            "gold": gold 
        })
    
        return {
            "number_of_potions": total_potions, 
            "ml_in_barrels": total_ml,
            "gold": gold 
        }

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"
