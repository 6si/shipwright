from shipwright import fn


@fn.curry
def f(x, y, z):
    return x + y + z


def test_curry():
    assert 6 == f(1, 2, 3) == f(1)(2, 3) == f(1)(2)(3) == f(1)()(2)()(3)
