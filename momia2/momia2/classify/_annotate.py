# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'simplified_particle_labler.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QKeySequence
from PIL import Image, ImageQt
from PyQt5.QtGui import QImage, QPainter, QPixmap, QPalette
import sys
from functools import partial


class ParticleLabelerMain(QtWidgets.QWidget):

    def __init__(self, images=[], label_dict={}, annot=[], *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        if len(images) > 0:
            self.images = images
        else:
            self.images = [(np.random.random((50, 50)) * 255).astype(np.uint8) for i in range(5)]
        if len(annot) == 0:
            self.annotation = np.zeros(len(self.images))
        else:
            self.annotation = annot
        self.default_labeldict = label_dict
        self.mainwindow = QtWidgets.QMainWindow()
        self.setupUi(self.mainwindow)

    def setupUi(self, MainWindow):
        self.Nlablers = 2
        self.MaxNlablers = 10
        self.labelers = []
        self.counter = np.where(self.annotation == 0)[0][0]
        self.Nimage = len(self.images)
        self.enableFastLabelMode = False
        MainWindow.setObjectName("ParticleLablerMain")
        MainWindow.resize(791, 599)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.particle_viewer_container = QtWidgets.QGroupBox(self.centralwidget)
        self.particle_viewer_container.setGeometry(QtCore.QRect(10, 10, 501, 511))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(13)
        self.particle_viewer_container.setFont(font)
        self.particle_viewer_container.setObjectName("particle_viewer_container")
        self.particle_viewer = QtWidgets.QLabel(self.particle_viewer_container)
        self.particle_viewer.setBackgroundRole(QPalette.Base)
        self.particle_viewer.setGeometry(QtCore.QRect(10, 30, 481, 461))
        self.particle_viewer.setObjectName("particle_viewer")
        self.particle_scroller = QtWidgets.QScrollBar(self.particle_viewer_container)
        self.particle_scroller.setGeometry(QtCore.QRect(10, 490, 421, 20))
        self.particle_scroller.setOrientation(QtCore.Qt.Horizontal)
        self.particle_scroller.setInvertedAppearance(False)
        self.particle_scroller.setInvertedControls(False)
        self.particle_scroller.setRange(1, self.Nimage)
        self.particle_scroller.setObjectName("particle_scroller")
        self.particle_scroller.valueChanged.connect(self.scroll_action)
        self.particle_N_track = QtWidgets.QLabel(self.particle_viewer_container)
        self.particle_N_track.setGeometry(QtCore.QRect(430, 490, 60, 16))
        self.particle_N_track.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.particle_N_track.setObjectName("particle_N_track")
        font = QtGui.QFont()
        font.setPointSize(11)
        self.particle_info = QtWidgets.QLabel(MainWindow)
        self.particle_info.setGeometry(QtCore.QRect(200, 10, 300, 30))
        self.particle_info.setAlignment(QtCore.Qt.AlignRight)
        self.particle_info.setObjectName("particle_info")

        self.labler_container = QtWidgets.QGroupBox(self.centralwidget)
        self.labler_container.setGeometry(QtCore.QRect(520, 10, 261, 511))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(13)
        self.labler_container.setFont(font)
        self.labler_container.setObjectName("labler_container")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.labler_container)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(9, 50, 241, 451))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.hotkey = QtWidgets.QLabel(self.labler_container)
        self.hotkey.setGeometry(QtCore.QRect(0, 30, 51, 16))
        self.hotkey.setAlignment(QtCore.Qt.AlignCenter)
        self.hotkey.setObjectName("hotkey")
        self.class_name_header = QtWidgets.QLabel(self.labler_container)
        self.class_name_header.setGeometry(QtCore.QRect(100, 30, 81, 16))
        self.class_name_header.setAlignment(QtCore.Qt.AlignCenter)
        self.class_name_header.setObjectName("class_name_header")
        self.revert2default_button = QtWidgets.QPushButton(self.centralwidget)
        self.revert2default_button.setGeometry(QtCore.QRect(290, 530, 131, 32))
        self.revert2default_button.setMouseTracking(False)
        self.revert2default_button.setAutoDefault(False)
        self.revert2default_button.setObjectName("revert2default_button")
        self.finish_labeling_button = QtWidgets.QPushButton(self.centralwidget)
        self.finish_labeling_button.setGeometry(QtCore.QRect(420, 530, 91, 32))
        self.finish_labeling_button.setObjectName("finish_labeling_button")
        self.finish_labeling_button.clicked.connect(self.safeExit)

        self.add_Class_button = QtWidgets.QPushButton(self.centralwidget)
        self.add_Class_button.setGeometry(QtCore.QRect(520, 530, 60, 32))
        self.add_Class_button.setObjectName("add_Class_button")
        self.add_Class_button.clicked.connect(self.addClass)
        self.del_Class_button = QtWidgets.QPushButton(self.centralwidget)
        self.del_Class_button.setGeometry(QtCore.QRect(580, 530, 60, 32))
        self.del_Class_button.setObjectName("dell_Class_button")
        self.del_Class_button.clicked.connect(self.delClass)

        self.prev_particle_button = QtWidgets.QPushButton(self.centralwidget)
        self.prev_particle_button.setGeometry(QtCore.QRect(10, 530, 131, 32))
        self.prev_particle_button.setObjectName("prev_particle_button")
        self.prev_particle_button.clicked.connect(self.previous_image)
        self.next_particle_button = QtWidgets.QPushButton(self.centralwidget)
        self.next_particle_button.setGeometry(QtCore.QRect(140, 530, 131, 32))
        self.next_particle_button.setObjectName("next_particle_button")
        self.next_particle_button.clicked.connect(self.next_image)
        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setGeometry(QtCore.QRect(270, 530, 20, 31))
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.line_2 = QtWidgets.QFrame(self.centralwidget)
        self.line_2.setGeometry(QtCore.QRect(510, 530, 20, 31))
        self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.label_mode = QtWidgets.QPushButton(self.centralwidget)
        self.label_mode.setGeometry(QtCore.QRect(640, 530, 149, 32))
        self.label_mode.setObjectName("label_mode")
        self.label_mode.clicked.connect(self.startAnnotation)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.retranslateUi(MainWindow)
        self.presetLablers(label_dict=self.default_labeldict)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.display_n()
        self.prev_butt_shortcut = QtWidgets.QShortcut(QKeySequence("Left"), self.prev_particle_button)
        self.prev_butt_shortcut.activated.connect(self.previous_image)
        self.next_butt_shortcut = QtWidgets.QShortcut(QKeySequence("Right"), self.next_particle_button)
        self.next_butt_shortcut.activated.connect(self.next_image)
        self.initLablerShortcut()
        self.watchFastLabel()
        self.update_scroller()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.particle_viewer_container.setTitle(_translate("MainWindow", "Particle viewer"))
        self.particle_N_track.setText(_translate("MainWindow", "1/{}".format(self.Nimage)))
        self.labler_container.setTitle(_translate("MainWindow", "Class labeler"))
        self.hotkey.setText(_translate("MainWindow", "Hotkey"))
        self.class_name_header.setText(_translate("MainWindow", "Class name"))
        self.revert2default_button.setText(_translate("MainWindow", "Revert to default"))
        self.finish_labeling_button.setText(_translate("MainWindow", "FINISH"))
        self.add_Class_button.setText(_translate("MainWindow", "+"))
        self.del_Class_button.setText(_translate("MainWindow", "-"))
        self.prev_particle_button.setText(_translate("MainWindow", "Previous (<-)"))
        self.next_particle_button.setText(_translate("MainWindow", "Next (->)"))
        self.label_mode.setText(_translate("MainWindow", "Start annotation"))
        self.update_particle_info()

    def presetLablers(self, label_dict={}, enable_edit=False):
        _translate = QtCore.QCoreApplication.translate
        self.Nlablers = max(2, len(label_dict))
        for i in range(self.MaxNlablers):
            idx = i + 1
            key = (i + 1) % 10
            if idx > self.Nlablers:
                hide = True
            else:
                hide = False
            font = QtGui.QFont()
            font.setFamily("Arial")
            font.setPointSize(12)
            widget = QtWidgets.QWidget(self.verticalLayoutWidget)
            widget.setObjectName("class_{}_widget".format(idx))
            label = QtWidgets.QLabel(widget)
            label.setGeometry(QtCore.QRect(0, 1, 31, 20))
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setObjectName("class_{}_label".format(idx))
            name = QtWidgets.QLineEdit(widget)
            name.setGeometry(QtCore.QRect(32, 0, 201, 21))
            name.setObjectName("class_{}_name".format(idx))
            name.setFont(font)
            label.setFont(font)
            label.setText(_translate('MainWindow', str(key)))
            name.setText(_translate('MainWindow', 'Class {}'.format(idx)))
            if idx in label_dict:
                name.setText(_translate('MainWindow', label_dict[idx]))
            self.verticalLayout.addWidget(widget)
            if hide:
                name.setEnabled(False)
                name.hide()
                label.hide()
            self.labelers.append([widget, label, name])
            if enable_edit:
                self._enable_edit(True)
            else:
                self._enable_edit(False)

    def addClass(self):
        n = min(self.Nlablers, self.MaxNlablers - 1)
        widget, label, name = self.labelers[n]
        name.setEnabled(True)
        name.show()
        label.show()
        self.Nlablers = min(self.Nlablers + 1, self.MaxNlablers - 1)

    def delClass(self):
        n = max(self.Nlablers - 1, 0)
        widget, label, name = self.labelers[n]
        name.setEnabled(False)
        name.hide()
        label.hide()
        self.Nlablers = max(self.Nlablers - 1, 0)

    def startAnnotation(self):
        if self.label_mode.text() == "Start annotation":
            self._enable_edit(False)
        else:
            self._enable_edit(True)

    def _enable_edit(self, edit_on=True):
        if not edit_on:
            for widget, label, name in self.labelers:
                name.setEnabled(False)
                self.label_mode.setText('Edit class labels')
            self.add_Class_button.setEnabled(False)
            self.del_Class_button.setEnabled(False)
            self.enableFastLabelMode = True
        else:
            for widget, label, name in self.labelers:
                name.setEnabled(True)
                self.label_mode.setText('Start annotation')
            self.add_Class_button.setEnabled(True)
            self.del_Class_button.setEnabled(True)
            self.enableFastLabelMode = False

    def update_scroller(self):
        self.particle_scroller.setValue(self.counter + 1)
        self.update_particle_tracker()

    def scroll_action(self):
        self.counter = self.particle_scroller.value() - 1
        self.display_n()
        self.update_particle_tracker()

    def update_particle_tracker(self):
        _translate = QtCore.QCoreApplication.translate
        self.particle_N_track.setText(_translate("MainWindow", "{}/{}".format(self.counter + 1, self.Nimage)))

    def initLablerShortcut(self):
        self.shortcuts = []
        for i in range(len(self.labelers)):
            shortcut = str((i + 1) % 10)
            shortcut_obj = QtWidgets.QShortcut(QKeySequence(shortcut), self.next_particle_button)
            self.shortcuts.append(shortcut_obj)

    def initFastLabel(self, annot):
        if self.enableFastLabelMode and annot < self.Nlablers:
            self.annotation[self.counter] = annot + 1
            self.next_image()

    def watchFastLabel(self):
        for i, v in enumerate(self.shortcuts):
            func = partial(self.initFastLabel, i)
            v.activated.connect(func)

    def _display_image(self, pil_img):
        shape = pil_img.size
        if shape[1] > shape[0]:
            pil_img = pil_img.transpose(Image.ROTATE_90)
            shape = pil_img.size
        hcenter = 261
        wcenter = 251
        max_half_height = 230
        max_half_width = 240
        relative_height = shape[1] / shape[0]
        trimmed_half_height = int(round(relative_height * max_half_height))

        new_window_width = 2 * trimmed_half_height

        self.particle_viewer.setGeometry(QtCore.QRect(10, hcenter - trimmed_half_height, 481, new_window_width))
        img = ImageQt.ImageQt(pil_img)
        self.particle_viewer.setPixmap(QPixmap.fromImage(img))
        self.particle_viewer.setScaledContents(True)

    def update_particle_info(self):
        _translate = QtCore.QCoreApplication.translate
        n = self.counter + 1
        class_id = int(self.annotation[self.counter])
        if class_id == 0:
            info = "Particle {} hasn't been annotated.".format(n)
        else:
            class_label = self.labelers[class_id - 1][2].text()
            info = "Particle {} is annotated as class: {} ({})".format(n, class_id, class_label)
        self.particle_info.setText(_translate("MainWindow", info))

    def display_n(self):
        self._display_image(self.images[self.counter])
        self.update_particle_info()

    def previous_image(self):
        self.counter = max(0, self.counter - 1)
        self.update_scroller()
        self.display_n()

    def next_image(self):
        self.counter = min(self.Nimage - 1, self.counter + 1)
        self.update_scroller()
        self.display_n()

    def safeExit(self):
        """exit the application gently so Spyder IDE will not hang"""
        self.mainwindow.deleteLater()
        self.mainwindow.close()
        self.mainwindow.destroy()


def run_particle_labeler(images=[(np.random.random((100, 50)) * 255).astype(np.uint8) for i in range(100)],
                         label_dict={1: 'single cell', 2: 'microcolony', 3: 'others'},
                         annot=[]):
    # if __name__ == '__main__':
    app = QtCore.QCoreApplication.instance()
    app = None
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
        app.aboutToQuit.connect(app.deleteLater)
        main = ParticleLabelerMain(images=images, label_dict=label_dict, annot=annot)
        main.mainwindow.show()
        app.exec_()