import sys

import pytest

try:
    import impreproc
except ImportError as e:
    raise ImportError(e)


def run_tests():
    retcode = pytest.main()
    sys.exit(retcode)


def run_gui():
    from PyQt5.QtWidgets import QApplication

    from impreproc.gui import dji2metashape

    # Run GUI
    app = QApplication(sys.argv)
    window = dji2metashape.MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()
