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
        gold = connection.execute(sqlalchemy.text("SELECT SUM(change) AS gold FROM gold_ledger")).scalar_one()
        ml = connection.execute(sqlalchemy.text(
            """
            SELECT
            SUM(change_red_ml) AS num_red_ml,
            SUM(change_green_ml) AS num_green_ml,
            SUM(change_blue_ml) AS num_blue_ml,
            SUM(change_dark_ml) AS num_dark_ml
            FROM ml_ledger
            """
        )).first()
        num_potions = connection.execute(sqlalchemy.text("SELECT SUM(change) AS num_potions FROM item_ledger")).scalar_one()

        total_ml = ml.num_red_ml + ml.num_green_ml + ml.num_blue_ml + ml.num_dark_ml

        log("Audit", {
            "number_of_potions": num_potions, 
            "ml_in_barrels": total_ml,
            "gold": gold 
        })
    
        return {
            "number_of_potions": num_potions, 
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
