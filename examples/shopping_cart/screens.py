import typing as t

from mobilex import Request
from mobilex.response import redirect
from mobilex.router import Router
from mobilex.screens import Action, Screen

from .models import Cart, CartItem, Product, all_products, get_product

router = Router(f"shopping_cart")


@router.start_screen("home")
class HomeScreen(Screen):
    actions = [
        Action("Catalog", screen="catalog"),
        Action("Cart", screen="cart"),
        Action("My account", screen="account"),
    ]

    nav_actions = []

    def init(self, *a):
        self.session.setdefault("cart", {})

    def render(self):
        self.print(f"Welcome to Fruit Bar.")


@router.screen("catalog")
class CatalogScreen(Screen):
    def get_actions(self):
        if not (menu := self.state.get("product_menu")):
            products = all_products()
            self.state.product_menu = menu = [
                Action(
                    f"{item.name:<10}- {item.price:.2f}/Kg",
                    screen="product",
                    kwargs={"product_id": item.id},
                )
                for item in products
            ]
        return menu

    async def render(self):
        self.print(f"Select a product.")


@router.screen("product")
class ProductScreen(Screen):
    @property
    def product(self):
        return get_product(self.state.product_id)

    def get_nav_actions(self) -> list[Action]:
        return [
            Action(
                "Add to Cart",
                screen="add_to_cart",
                kwargs=dict(product_id=self.product.id),
            ),
            *super().get_nav_actions(),
        ]

    async def render(self):
        product = self.product
        self.print(f"#{product.id} {product.name}")
        self.print(f"Price per Kg: {product.price:.2f}/=")
        self.print(f"Details:")
        self.print(product.description)

        return self.CON


@router.screen("add_to_cart")
class AddToCartScreen(Screen):
    @property
    def product(self):
        return get_product(self.state.product_id)

    async def handle(self, qty: str):
        qty = round(float(qty.lower().replace("kg", "").strip()), 3)
        if qty >= 0.001:
            cart = self.session["cart"]
            cart[self.product.id] = qty
            await self.request.history.pop()
            return redirect("cart", added=self.product.id)
        self.print("Invalid value!")
        self.print("Must be between 0.001 and 1000")

    async def render(self):
        product = self.product
        self.print(f"How much {product.name} in Kgs do what.")
        self.print(f"Eg. 0.5 for 0.5Kg, 3 for 3Kg.")
        self.print(f"Price per Kg: {product.price:.2f}/=")
        return self.CON


@router.screen("cart")
class CartScreen(Screen):
    actions = [
        Action("Checkout", screen="checkout"),
        Action("Add more", screen="catalog"),
        Action("Remove items", screen="catalog"),
    ]

    def get_cart_products(self):
        cart = self.session["cart"]
        return {get_product(id): qty for id, qty in cart.items()}

    # async def handle(self, inpt: str):
    #     inpt = round(float(inpt.lower().replace("kg", "").strip()), 3)
    #     if inpt >= 0.001:
    #         return redirect("cart", added=self.product.id)
    #     self.print("Invalid value!")

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


@router.screen("checkout")
class CheckoutScreen(Screen):
    actions = [
        Action("Checkout", screen="checkout"),
        Action("Add more", screen="catalog"),
        Action("Remove items", screen="catalog"),
    ]

    def get_cart_products(self):
        cart = self.session["cart"]
        return {get_product(id): qty for id, qty in cart.items()}

    async def handle(self, inpt: str):
        inpt = round(float(inpt.lower().replace("kg", "").strip()), 3)
        if inpt >= 0.001:
            return redirect("cart", added=self.product.id)
        self.print("Invalid value!")

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
