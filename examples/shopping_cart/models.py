from dataclasses import dataclass, field
from random import choice


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: int
    description: str = "\n".join(
        (
            "Discover a captivating fruit ",
            "with radiant, translucent allure,",
            "its colors shifting in a mesmerizing dance.",
            "Its enchanting flavors rejuvenate the body",
            "and uplift the spirit, offering a truly",
            "magical experience for all who partake.",
        )
    )


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
