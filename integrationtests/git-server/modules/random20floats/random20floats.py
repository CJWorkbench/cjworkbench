import numpy
import pandas


def fetch(params):
    numpy.random.seed(None)
    return pandas.DataFrame({"data": numpy.random.randn(20)})
