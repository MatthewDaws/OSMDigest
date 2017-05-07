import sys
sys.path.insert(0, "..")

import osmdigest.sqlite as sq
import os

for x in sq.convert_gen(os.path.join("..","..","..","data","california-latest.osm.xz"),
          os.path.join("..","..","..","data","california-latest.db")):
    print(x)