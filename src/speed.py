# -*- coding: utf-8 -*-
from enum import IntEnum

class Speed(IntEnum):
    ZERO          = 0
    QUADRATIC     = 100
    QUADRATIC_LOG = 200
    CUBIC         = 300
    POLYNOMIAL    = 400
    EXPONENTIAL   = 500
