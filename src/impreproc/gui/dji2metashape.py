import configparser
import logging
import os
import sys
from pathlib import Path

import guidata
import guidata.dataset.dataitems as di
import guidata.dataset.datatypes as dt
import numpy as np
from guidata.configtools import get_icon
from guidata.dataset.qtwidgets import DataSetEditGroupBox, DataSetShowGroupBox
from guidata.qthelpers import add_actions, create_action, get_std_icon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplitter

import impreproc.dji as dji

_app = guidata.qapplication()  # not required if a QApplication has already been created

# read parameters from ini file -----------------------------------------------
iniFile = "dji2metashape.ini"

# set default values of flags -------------------------------------------------
exportTXT = dt.ValueProp(False)
isCSVflag = dt.ValueProp(True)
isXLSflag = dt.ValueProp(True)
isStdscaleflag = dt.ValueProp(False)
isUTMflag = dt.ValueProp(False)
isRAWflag = dt.ValueProp(True)
isConvertRAWflag = dt.ValueProp(False)
utmZones = ["32N", "33N", "34N"]


# GUI classes -------------------------------------------------------------------
class gui_dji2metashape(dt.DataSet):
    """
    convert dji log file for metashape usage
    """

    # _bg1 = dt.BeginGroup('Input')
    logfile = di.FileOpenItem("Drone log file:", formats=["*"]).set_pos(
        col=0, colspan=7
    )
    imgfold = di.DirectoryItem("Image folder:").set_pos(col=0, colspan=7)
    fileExtension = di.ChoiceItem(
        "Format:", ((False, "JPG"), (True, "DNG")), default=False
    ).set_pos(col=7, colspan=1)
    fileExtension = fileExtension.set_prop("display", store=isRAWflag)
    fileExtension = fileExtension.set_prop("display", active=False)
    # _eg1 = dt.EndGroup('Input')

    # _bg2 = dt.BeginGroup('Output coordinates')
    isUTM = di.ChoiceItem(
        "Projection:",
        [(False, "Geographic (Lat/Lon/h)"), (True, "UTM (E/N/h)")],
        radio=True,
    ).set_pos(col=0, colspan=4)
    utmZone = di.ChoiceItem("Zone:", utmZones).set_pos(col=5, colspan=3)
    useImageCoord = di.ChoiceItem(
        "Input coordinates:",
        [
            (False, "Coordinates from log file"),
            (True, "Coordinates from image EXIF metadata"),
        ],
        radio=True,
    )

    isUTM.set_prop("display", store=isUTMflag)
    utmZone.set_prop("display", active=isUTMflag)
    # _eg2 = dt.EndGroup('Output coordinates')

    isStdscale = di.BoolItem(
        "Apply the following standard deviation scale factors",
        default=isStdscaleflag.value,
    )
    isStdscale.set_prop("display", store=isStdscaleflag)

    _bg3 = dt.BeginGroup("").set_prop("display", active=isStdscaleflag)
    fixed_stdscale = di.FloatItem(
        "Fixed GNSS solutions       \tScale factor:", default=1, min=0, nonzero=1
    ).set_pos(col=0, colspan=1)
    fixed_flagval = di.IntItem("Flag in MRK file:", default=50).set_pos(
        col=1, colspan=1
    )
    float_stdscale = di.FloatItem(
        "Float GNSS solutions       \tScale factor:", default=1, min=0, nonzero=1
    )
    float_flagval = di.IntItem("Flag in MRK file:", default=16).set_pos(
        col=1, colspan=1
    )
    auton_stdscale = di.FloatItem(
        "Autonomous GNSS solutions\tScale factor:", default=1, min=0, nonzero=1
    )
    auton_flagval = di.IntItem("Flag in MRK file:", default=1).set_pos(col=1, colspan=1)
    # fixed_stdscale.set_prop('display', active=isStdscaleflag)
    # fixed_flagval.set_prop('display', active=isStdscaleflag)
    # float_stdscale.set_prop('display', active=isStdscaleflag)
    # float_flagval.set_prop('display', active=isStdscaleflag)
    # auton_stdscale.set_prop('display', active=isStdscaleflag)
    # auton_flagval.set_prop('display', active=isStdscaleflag)
    _eg3 = dt.EndGroup("")

    # _bg4 = dt.BeginGroup('Output')
    isCSV = (
        di.BoolItem("Metashape CSV file:", default=isCSVflag.value)
        .set_prop("display", store=isCSVflag)
        .set_pos(col=0, colspan=1)
    )
    csvfile = (
        di.FileSaveItem("", ("csv"))
        .set_prop("display", active=isCSVflag)
        .set_pos(col=1, colspan=7)
    )

    isXLS = (
        di.BoolItem("Excel file:", default=isXLSflag.value)
        .set_prop("display", store=isXLSflag)
        .set_pos(col=0, colspan=1)
    )
    xlsfile = (
        di.FileSaveItem("", ("xlsx"))
        .set_prop("display", active=isXLSflag)
        .set_pos(col=1, colspan=7)
    )

    convRAW = (
        di.BoolItem("Store converted RAWs in:", default=isConvertRAWflag.value)
        .set_prop("display", active=isRAWflag, store=isConvertRAWflag)
        .set_pos(col=0, colspan=1)
    )
    jpgfold = (
        di.DirectoryItem("")
        .set_prop("display", active=isConvertRAWflag)
        .set_pos(col=1, colspan=7)
    )
    # _eg4 = dt.EndGroup('Output')


class gui_setting(dt.DataSet):
    """Settings"""

    # Check if a config file exists, otherwise use default values
    if not Path(iniFile).exists():
        logging.info("Config file not found. Using default values.")
        rtroot = None
        rtprofile = None
        rtoptions = None
    else:
        config = configparser.ConfigParser()
        config.read(iniFile)

        rtroot = config["RAW"]["rtroot"]
        if rtroot == "None":
            rtroot = None

        rtprofile = config["RAW"]["rtprofile"]
        if rtprofile == "None":
            rtprofile = None

        rtoptions = config["RAW"]["rtoptions"]
        if rtoptions == "None":
            rtoptions = None

    rtroot = di.DirectoryItem("RAW Therapee folder:", default=rtroot)
    rtprofile = di.FileOpenItem("RAW Therapee profile:", "pp3", default=rtprofile)
    rtoptions = di.TextItem("RAW Therapee cmd options:", default=rtoptions)


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.resize(500, 10)
        self.setWindowIcon(get_icon("python.png"))
        self.setWindowTitle("dji2metashape")

        # Instantiate dataset-related widgets:
        self.groupbox1 = DataSetEditGroupBox(
            "", gui_dji2metashape, button_text="Convert", comment=""
        )
        self.groupbox1.SIG_APPLY_BUTTON_CLICKED.connect(self.makeconversion)

        # settings
        self.groupbox2 = DataSetEditGroupBox(
            "",
            gui_setting,
            icon=get_std_icon("FileDialogDetailedView"),
            title="Settings",
            comment="",
        )

        # splitter = QSplitter(Qt.Vertical)
        splitter = QSplitter(self)
        splitter.addWidget(self.groupbox1)
        self.setCentralWidget(splitter)
        # self.setContentsMargins(10, 5, 10, 5)

        # File menu
        file_menu = self.menuBar().addMenu("File")
        quit_action = create_action(
            self,
            "Quit",
            shortcut="Ctrl+Q",
            icon=get_std_icon("DialogCloseButton"),
            tip="Quit application",
            triggered=self.close,
        )
        # Edit menu
        edit_menu = self.menuBar().addMenu("Edit")
        setting_action = create_action(
            self,
            "Settings...",
            tip="Settings...",
            icon=get_std_icon("FileDialogDetailedView"),
            triggered=self.setting_window,
        )

        add_actions(file_menu, (quit_action,))
        add_actions(edit_menu, (setting_action,))

    def makeconversion(self):
        try:
            # make conversion
            data = self.groupbox1.dataset
            settings = self.groupbox2.dataset

            data_dir = data.imgfold
            mrk_file = data.logfile
            if data.fileExtension:
                image_ext = "dng"
            else:
                image_ext = "jpg"

            mrk_dict = dji.mrkread(mrk_file)
            exif_dict = dji.get_images(data_dir, image_ext)
            merged_data = dji.merge_mrk_exif_data(mrk_dict, exif_dict)

            if data.isXLS == True:
                if data.isStdscale == True:
                    dji.dji2xlsx(
                        merged_data,
                        data.xlsfile,
                        flag_utm=int(data.isUTM),
                        utm_zone=utmZones[data.utmZone],
                        flag_qual=[
                            data.fixed_flagval,
                            data.float_flagval,
                            data.auton_flagval,
                        ],
                        scale_factors=[
                            data.fixed_stdscale,
                            data.float_stdscale,
                            data.auton_stdscale,
                        ],
                    )
                else:
                    dji.dji2xlsx(
                        merged_data,
                        data.xlsfile,
                        flag_utm=int(data.isUTM),
                        utm_zone=utmZones[data.utmZone],
                    )

            if data.isCSV == True:
                pass

            # done message
            msg = QMessageBox(parent=self)
            msg.setIcon(QMessageBox.Information)
            msg.setText("File correctly converted!")
            msg.setWindowTitle("dji2metashape")
            msg.setStandardButtons(QMessageBox.Ok)
            retval = msg.exec_()
            # clean the fields
            # self.groupbox1.dataset.fin = ''
            # self.groupbox1.dataset.fout = ''
            # self.groupbox1.get()
        except:
            # error message
            # TODO: catch the error type and show a different message for each type of error.
            msg = QMessageBox(parent=self)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error during file conversion!")  # TODO: add the error type
            msg.setWindowTitle("Done")
            msg.setStandardButtons(QMessageBox.Ok)
            retval = msg.exec_()

    def setting_window(self):
        if self.groupbox2.dataset.edit(parent=self, size=(600, 10)):
            config = self.groupbox2.dataset.config
            config["RAW"]["rtroot"] = self.groupbox2.dataset.rtroot
            config["RAW"]["rtprofile"] = self.groupbox2.dataset.rtprofile
            with open(iniFile, "w") as configfile:  # save
                config.write(configfile)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
