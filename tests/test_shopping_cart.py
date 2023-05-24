import pytest

from examples.shopping_cart import models, screens
from mobilex import App, Request


@pytest.fixture
def app(app):
    return screens.app


async def test_basic(app: App):
    msisdn = "123456"
    req_0 = Request(msisdn, ussd_string="")
    res_0: str = await app(req_0)
    req_1 = Request(msisdn, ussd_string="1*2*1*1.5*2*8*1*2*00*1*99")
    res_1: str = await app(req_1)

    session, products = req_1.session, models.all_products()
    cart_ex = {products[i].id: v for i, v in ((1, 1.5), (7, 2))}
    del products
    argv, args = session.argv, req_1.args
    arg_str = f"{argv!s} {argv!r} {argv.base_code =}, {argv.service_code}"

    cart = session["cart"]
    assert cart == cart_ex

    state = session.state
    state.reset("screen")
