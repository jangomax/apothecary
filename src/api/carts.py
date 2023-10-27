from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth
from enum import Enum

import sqlalchemy
from src import database as db

from src.discord import log

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    # with db.engine.begin() as connection:
    #     result = connection.execute(sqlalchemy.text(
    #         """
    #         SELECT * FROM cart_item
    #         JOIN catalog_item ON cart_item.item_id = catalog_item.id
    #         JOIN carts ON cart_item.cart_id = carts.id
    #         """))

    if sort_col is search_sort_options.customer_name:
        order_by = " customer_name "
    elif sort_col is search_sort_options.item_sku:
        order_by = " sku "
    elif sort_col is search_sort_options.line_item_total:
        order_by = " total "
    elif sort_col is search_sort_options.timestamp:
        order_by = " time "
    else:
        raise HTTPException(400, detail="Cannot sort by property.")

    stmt = """
        SELECT catalog_item.sku, cart_item.quantity * price AS total, time
        FROM cart_item
        JOIN catalog_item ON cart_item.item_id = catalog_item.id
        JOIN carts ON cart_item.item_id = carts.id AND cart_item.cart_id = carts.id
    """

    stmt += f" ORDER BY {order_by} {search_sort_options.sort_order}"
    stmt += f" LIMIT 5 {('OFFSET ' + int(search_page)) if search_page != '' else ('')}"

    # filter only if name parameter is passed
    if potion_sku != "" and customer_name != "":
        stmt += f" WHERE catalog_item.sku ILIKE %{potion_sku}% AND carts.customer_name ILIKE %{customer_name}"
    elif potion_sku != "":
        stmt += f" WHERE catalog_item.sku ILIKE %{potion_sku}%"
    elif customer_name != "":
        stmt += f" WHERE carts.customer_name ILIKE %{customer_name}%"

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(stmt))
        line_items = []
        for i, row in enumerate(result):
            line_items.append(
                {
                    "line_item_id": i,
                    "item_sku": row.sku,
                    "customer_name": row.customer_name,
                    "line_item_total": row.quantity * row.price,
                    "timestamp": row.time
                }
            )

    return {
        "previous": str(int(search_page) - 5) if int(search_page) > 5 else None,
        "next": str(int(search_page) + 5),
        "results": line_items
    }


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
            SELECT catalog_item.sku, cart_item.quantity
            FROM cart_item
            JOIN catalog_item ON cart_item.item_id = catalog_item.id
            JOIN (
              SELECT sku, SUM(change) as quantity
              FROM item_ledger
              GROUP BY sku
            ) AS inventory ON inventory.sku = catalog_item.sku
            WHERE cart_item.cart_id = :cart_id AND inventory.quantity < cart_item.quantity
            """
        ), {"cart_id": cart_id}).all()

        if len(notEnough) > 0:
            log("Transaction cancelled.", dict(notEnough))
            raise HTTPException(status_code=400, detail="Cart cannot be fulfilled.")

        orderLog = []

        transaction_id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO transactions (description)
            VALUES (:description)
            RETURNING id
            """
        ), {"description": f"Transaction in progress"}).scalar_one()

        # get all items in cart
        items = connection.execute(sqlalchemy.text(
            """
            SELECT sku, name, price, cart_item.quantity FROM catalog_item
            JOIN cart_item ON catalog_item.id = cart_item.item_id
            WHERE cart_item.cart_id = :cart_id AND catalog_item.id = cart_item.item_id
            """
        ), {"cart_id": cart_id})

        desc = ""

        for item in items:
            paid = item.quantity * item.price
            total_price += paid
            desc += f"{paid}g: {item.quantity}x {item.sku}, "
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO gold_ledger (change, transaction_id)
                VALUES (:change, :transaction_id)
                """
            ), {"change": paid, "transaction_id": transaction_id})

            connection.execute(sqlalchemy.text(
                """
                INSERT INTO item_ledger (sku, change, transaction_id)
                VALUES (:sku, :change, :transaction_id)
                """
                ), 
                {
                    "sku": item.sku,
                    "change": -(item.quantity),
                    "transaction_id": transaction_id
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
        connection.execute(sqlalchemy.text(
            """
            UPDATE transactions
            SET description = :description
            WHERE id = :transaction_id
            """
        ), {"description": desc[:-2], "transaction_id": transaction_id})
        log("Succesful Checkout!", {
            "total_potions_bought": total_qty, 
            "total_gold_paid": total_price,
            "items": orderLog
        })
        return {
            "total_potions_bought": total_qty, 
            "total_gold_paid": total_price
        }
