# to reset MAX30101, turn off led -- is good for debugging
from MAX30101 import *

dev = MAX30101()
dev.reset()
