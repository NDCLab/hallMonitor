import sys
import traceback

from hallmonitor import app, hmutils

try:
    app.main(hmutils.get_args())
except Exception as e:
    print("Unexpected error:", e)
    traceback.print_exc()
    sys.exit(1)
