"""`python3 -m expected [batch | --gdm]`: surface lists for run.sh (see the package docstring)."""
import sys

from . import SURFACES_GDM, surfaces_for

if len(sys.argv) > 1 and sys.argv[1] == "--gdm":
    print(",".join(sorted(SURFACES_GDM)))
else:
    print(",".join(surfaces_for(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else None)))
