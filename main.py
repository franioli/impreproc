import pytest
import sys

try:
    import impreproc
except ImportError as e:
    raise ImportError(e)

if __name__ == "__main__":
    retcode = pytest.main()

    sys.exit(retcode)
