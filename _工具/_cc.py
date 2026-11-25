
from moviepy import vfx
names=[n for n in dir(vfx) if not n.startswith("_")]
print("vfx:", names)
