import numpy
import pandas


def fetch(params):
    return pandas.DataFrame({"data": numpy.random.randn(20)})
