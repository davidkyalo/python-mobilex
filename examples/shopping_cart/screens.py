import typing as t


from mobilex import Request
from mobilex.screens import Screen
from mobilex.router import UssdRouter
from mobilex.response import redirect
from .models import all_products, get_product, Product, Cart, CartItem


router = UssdRouter(f"shopping_cart")


class SessionCartMixin:
    @property
    def cart(self) -> dict[int, float]:
        return self.session.setdefault("cart", {})


@router.start_screen("home")
class HomeScreen(SessionCartMixin, Screen):
    menu_items = {
        "1": ("Catalog", ".catalog"),
        "2": ("My Cart", ".cart"),
    }

    async def handle(self, inpt):
        if next := self.menu_items.get(inpt):
            return redirect(next[-1])
        self.print("Invalid choice!")

    async def render(self):
        self.print(f"Welcome to Fruit Bar.")
        for key, (label, _) in self.menu_items.items():
            self.print(f"{key}. {label}")
        return self.CON


@router.screen("catalog")
class CatalogScreen(Screen):
    def handle(self, inpt: str):
        menu: dict = self.state.product_menu
        product_id = menu.get(inpt)
        if product_id:
            return redirect(".product", product_id=product_id)
        self.print("Invalid choice!")

    async def render(self):
        self.print(f"Select a product.")
        products = all_products()
        product_menu = {}
        for i, product in enumerate(products, 1):
            self.print(f"{i}: {product.name:<10}- {product.price:.2f}/Kg")
            product_menu[f"{i}"] = product.id
        self.state.product_menu = product_menu
        return self.CON


@router.screen("product")
class ProductScreen(Screen):
    @property
    def product(self):
        return get_product(self.state.product_id)

    async def handle(self, inpt: str):
        if inpt == "1":
            return redirect(".add_to_cart", product_id=self.product.id)

    async def render(self):
        product = self.product
        self.print(f"#{product.id} {product.name}")
        self.print(f"Price per Kg: {product.price:.2f}/=")
        self.print(f"Details:")
        self.print(product.description)
        self.print("1. Add to Cart")

        return self.CON


@router.screen("add_to_cart")
class AddToCartScreen(SessionCartMixin, Screen):
    @property
    def product(self):
        return get_product(self.state.product_id)

    async def handle(self, qty: str):
        qty = round(float(qty.lower().replace("kg", "").strip()), 3)
        if qty >= 0.001:
            cart = self.cart
            cart[self.product.id] = qty
            return redirect(".cart", added=self.product.id)
        self.print("Invalid value!")

    async def render(self):
        product = self.product
        self.print(f"How much {product.name} in Kgs do what.")
        self.print(f"Eg. 0.5 for 0.5Kg, 3 for 3Kg.")
        self.print(f"Price per Kg: {product.price:.2f}/=")
        return self.CON


@router.screen("cart")
class CartScreen(SessionCartMixin, Screen):
    async def handle(self, inpt: str):
        inpt = round(float(inpt.lower().replace("kg", "").strip()), 3)
        if inpt >= 0.001:
            return redirect(".cart", added=self.product.id)
        self.print("Invalid value!")

    def get_cart_products(self):
        cart = self.cart
        return {get_product(id): qty for id, qty in cart.items()}

    async def render(self):
        cart = self.get_cart_products()
        total = sum(prod.price * qty for prod, qty in cart.items())
        self.print("Your shopping cart")
        self.print(f"{len(cart)} items. Total price: {total:.2f} /=")
        for i, (prod, qty) in enumerate(cart.items(), 1):
            self.print(
                f"{i:<2} {prod.name:<10} {prod.price:.2f} x {qty:2} - {prod.price * qty:.2f}/="
            )

        return self.CON
