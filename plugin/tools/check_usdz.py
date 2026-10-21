"""Check a USDZ for AR Quick Look with USD's own ARKit checker (usdchecker --arkit), in Blender.

    blender -b --factory-startup --python tools/check_usdz.py -- file.usdz

Prints `ARKIT ok` or `ARKIT FAIL <reason>` per failure, and `ANIM <first> <last>` when the
stage is animated.
"""
import sys

from pxr import Usd, UsdUtils

f = sys.argv[sys.argv.index("--") + 1]
c = UsdUtils.ComplianceChecker(arkit=True, skipARKitRootLayerCheck=False, rootPackageOnly=False,
                               skipVariants=False, verbose=False)
c.CheckCompliance(f)
bad = list(c.GetErrors()) + list(c.GetFailedChecks())
for b in bad:
    print("ARKIT FAIL", str(b)[:300], flush=True)
if not bad:
    print("ARKIT ok", flush=True)
st = Usd.Stage.Open(f)
# Animated: some attribute changes over time (Blender writes a frame range either way).
moving = any(a.GetNumTimeSamples() > 1 for p in st.Traverse() for a in p.GetAttributes())
if moving:
    print("ANIM", st.GetStartTimeCode(), st.GetEndTimeCode(), flush=True)
