from collections import abc
from dataclasses import dataclass, field
from decimal import Decimal
from random import choice
from typing_extensions import SupportsIndex


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: int
    description: str = "This is just a simple description for this product."


_products: dict[int, "Product"] = {
    id: Product(id=id, name=name, price=choice(range(10, 51, 5)))
    for id, name in enumerate(
        [
            "Apple",
            "Avocado",
            "Banana",
            "Berry",
            "Grape",
            "Lemon",
            "Mango",
            "Melon",
            "Orange",
            "Pear",
        ],
        10,
    )
}


def all_products() -> list[Product]:
    return [*_products.values()]


def get_product(id: int) -> Product | None:
    return _products.get(id)


@dataclass(frozen=True)
class CartItem:
    product_id: int
    quantity: float = field(compare=False)

    @property
    def product(self):
        return get_product(self.product_id)

    @property
    def price(self):
        return self.product.price * self.quantity


class Cart(set[CartItem]):
    @property
    def total_price(self) -> None:
        return sum(it.price for it in self)
