from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

carts = {} # Dict of lists [customer_name, qty]

class NewCart(BaseModel):
    customer: str


@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    id = abs(hash(new_cart.customer))
    carts[id] = [new_cart.customer, 0]
    return {"cart_id": id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    cart = carts[cart_id]

    return { 
        "cart_id": cart_id,
        "customer": cart[0],
        "qty_red": cart[1]
     }


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    if item_sku != "RED_POTION_0":
        return "OK"

    carts[cart_id][1] = cart_item.quantity
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_red_potions, gold FROM global_inventory"))
        row = result.first()
        cart = carts[cart_id]
        price = cart[1] * 50

        print(cart_checkout.payment)

        if cart[1] > row.num_red_potions:
            raise HTTPException(status_code=400, detail="Cart cannot be fulfilled.")

        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {row.gold + price}, num_red_potions = {row.num_red_potions - cart[1]}"))
        return {
            "total_potions_bought": cart[1], 
            "total_gold_paid": price
        }
