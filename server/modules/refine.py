import pandas as pd
import numpy as np
from .moduleimpl import ModuleImpl
import json
import logging


class Refine(ModuleImpl):

    def render(wf_module, table):

        return table