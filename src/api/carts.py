from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

from src.discord import log

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class NewCart(BaseModel):
    customer: str


@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(f"INSERT INTO carts (customer_name) VALUES (:customer) RETURNING id"), {"customer": new_cart.customer})
        id = result.scalar()
        log("Created New Cart", {
            "cart_id": id,
            "customer_name": new_cart.customer
        })
        return {"cart_id": id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(f"SELECT customer_name, qty_red, qty_green, qty_blue FROM carts WHERE id = {cart_id}"))
        row = result.first()
        log("Get Cart", { 
            "cart_id": cart_id,
            "customer": row.customer_name,
            "qty_red": row.qty_red,
            "qty_green": row.qty_green,
            "qty_blue": row.qty_blue,
        })
        return { 
            "cart_id": cart_id,
            "customer": row.customer_name,
            "qty_red": row.qty_red,
            "qty_green": row.qty_green,
            "qty_blue": row.qty_blue,
        }


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    valid_sku = {
        "RED_POTION_0": "qty_red", 
        "GREEN_POTION_0": "qty_green", 
        "BLUE_POTION_0": "qty_blue"
    }
    if not valid_sku.get(item_sku):
        return "OK"

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE carts SET {valid_sku[item_sku]} = {cart_item.quantity} WHERE id = {cart_id}"))
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    p_type = {
        "qty_red": "red",
        "qty_green": "green",
        "qty_blue": "blue",
    }

    with db.engine.begin() as connection:

        result = connection.execute(sqlalchemy.text(f"SELECT qty_red, qty_green, qty_blue FROM carts WHERE id = {cart_id}")).first()
        cart = {
            "red": result.qty_red,
            "green": result.qty_green,
            "blue": result.qty_blue,
        }

        total_price = 0
        total_qty = 0

        for item in p_type.values():
            in_stock = connection.execute(sqlalchemy.text(f"SELECT num_potions FROM potions WHERE color = '{item}'")).scalar()
            log(item, {"Requested": cart[item], "In Stock": in_stock})
            if cart[item] > in_stock:
                log("", {"Error": "Transaction cancelled."})
                raise HTTPException(status_code=400, detail="Cart cannot be fulfilled.")
        for item in p_type.values():
            connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = gold + {cart[item] * (50 if item == 'blue' else 5)}"))
            connection.execute(sqlalchemy.text(f"UPDATE potions SET num_potions = num_potions - {cart[item]} WHERE color = '{item}'"))
            total_price += cart[item] * (50 if item == "blue" else 5)
            total_qty += cart[item]
        connection.execute(sqlalchemy.text(f"UPDATE carts SET payment = '{cart_checkout.payment}' WHERE id = {cart_id}"))
        log("Succesful Checkout!", {
            "total_potions_bought": total_qty, 
            "total_gold_paid": total_price 
        })
        return {
            "total_potions_bought": total_qty, 
            "total_gold_paid": total_price
        }
