from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).first().gold
        potions = connection.execute(sqlalchemy.text("SELECT num_potions, num_ml FROM potions"))
        total_potions = 0
        total_ml = 0
        for color in potions:
            total_potions += color.num_potions
            total_ml += color.num_ml

    
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
