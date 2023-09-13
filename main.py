import sys

def run_tests():
    import pytest

    try:
        import impreproc
    except ImportError as e:
        raise ImportError(e)

    retcode = pytest.main()
    sys.exit(retcode)

def run_gui():
    from PyQt5.QtWidgets import QApplication

    from impreproc.gui import gui

    # Run GUI
    app = QApplication(sys.argv)
    window = gui.MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()
