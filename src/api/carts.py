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
        customer_name = connection.execute(sqlalchemy.text("""SELECT customer_name FROM carts WHERE id = :id"""), {"id": cart_id}).scalar_one()
        result = connection.execute(sqlalchemy.text(
            """
            SELECT sku, name, cart_item.quantity FROM catalog_item 
            JOIN cart_item ON cart_item.cart_id = :cart_id
            WHERE cart_item.item_id = catalog_item.id
            """), {"cart_id": cart_id})
        items = []
        for item in result:
            items.append({
                "sku": item.sku,
                "name": item.name,
                "quantity": item.quantity
            })
        log("Get Cart", { 
            "cart_id": cart_id,
            "customer": customer_name,
            "items": items
        })
        return { 
            "cart_id": cart_id,
            "customer": customer_name,
            "items": items
        }


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO cart_item (cart_id, item_id, quantity) 
                SELECT :cart_id, id, :qty 
                FROM catalog_item 
                WHERE sku = :item_sku
            """), {"cart_id": cart_id, "item_sku": item_sku, "qty": cart_item.quantity})
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    with db.engine.begin() as connection:

        total_price = 0
        total_qty = 0

        notEnough = connection.execute(sqlalchemy.text(
            """
            SELECT sku, cart_item.quantity FROM cart_item 
            JOIN catalog_item ON catalog_item.quantity < cart_item.quantity
            WHERE cart_item.cart_id = :cart_id AND catalog_item.id = cart_item.item_id
            """
        ), {"cart_id": cart_id}).all()

        if len(notEnough) > 0:
            log("Transaction cancelled.", dict(notEnough))
            raise HTTPException(status_code=400, detail="Cart cannot be fulfilled.")

        orderLog = []

        # get all items in cart
        items = connection.execute(sqlalchemy.text(
            """
            SELECT sku, name, price, cart_item.quantity FROM catalog_item
            JOIN cart_item ON catalog_item.id = cart_item.item_id
            WHERE cart_item.cart_id = :cart_id AND catalog_item.id = cart_item.item_id
            """
        ), {"cart_id": cart_id})

        for item in items:
            paid = item.quantity * item.price
            total_price += paid
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO gold_ledger VALUES (change, description)
                VALUES (:change, :description)
                """
            ), {"change": paid, "description": f"Sold {item.quantity}x {item.sku}"})

            connection.execute(sqlalchemy.text(
                """
                INSERT INTO item_ledger VALUES (sku, change, description)
                VALUES (:sku, :change, :description)
                """
                ), 
                {
                    "sku": item.sku,
                    "change": -(item.quantity),
                    "description": f"Sold {item.quantity}x {item.sku}"
                }
            )
            orderLog.append({
                "sku": item.sku,
                "name": item.name,
                "quantity": item.quantity
            })
            total_qty += item.quantity

        connection.execute(sqlalchemy.text(
            """
            UPDATE carts SET 
            payment = :payment,
            fulfilled = TRUE
            WHERE id = :cart_id
            """
        ), {"payment": cart_checkout.payment, "cart_id": cart_id})
        log("Succesful Checkout!", {
            "total_potions_bought": total_qty, 
            "total_gold_paid": total_price,
            "items": orderLog
        })
        return {
            "total_potions_bought": total_qty, 
            "total_gold_paid": total_price
        }
