import qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import errorDisplay

import os.path as osp
import csv
import numpy as np
from copy import deepcopy
import locale
locale.setlocale(locale.LC_ALL, '')

from Resources.measurements import MEASUREMENTS
from Resources.landmarks import LANDMARKS

MODULE_PATH = osp.dirname(__file__)
#
# BoneAngleMeterModule
#

class BoneAngleMeterModule(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Bone Angle Meter"
    self.parent.categories = ["Measurements"]
    self.parent.dependencies = []
    self.parent.contributors = ["Juliette Burg"]
    self.parent.helpText = """
This is a module for measuring bone angles based on landmarks.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
Developed during Juliette's doctorate at CTK, LMU Munich.
"""


class BoneAngleMeterModuleWidget(ScriptedLoadableModuleWidget):
    """
    Base widget that manages the measurement groups
    """

    SEGMENTATION_NODE_NAME = "Automatic Bone Segmentation Node"

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        #####################
        # GUI and connections
        #####################
        # Measurement buttons
        self.left_button = qt.QPushButton("Measurements Left")
        self.left_button.connect('clicked(bool)', self.onLeftDialogButton)
        self.layout.addWidget(self.left_button)

        self.right_button = qt.QPushButton("Measurements Right")
        self.right_button.connect('clicked(bool)', self.onRightDialogButton)
        self.layout.addWidget(self.right_button)

        # Automatic Segmentation
        segmentation_collapsible_button = ctk.ctkCollapsibleButton()
        segmentation_collapsible_button.text = "3D Segmentation"
        self.layout.addWidget(segmentation_collapsible_button)
        segmentation_form_layout = qt.QFormLayout(segmentation_collapsible_button)
        self.apply_segmentation_button = qt.QPushButton("Apply")
        self.apply_segmentation_button.connect('clicked(bool)', self.onApplySegmentation)
        segmentation_form_layout.addRow("Segmentation", self.apply_segmentation_button)

        self.threshold_lower = qt.QSpinBox()
        self.threshold_lower.setRange(-3000, 3000)
        self.threshold_lower.setValue(300)
        self.threshold_upper = qt.QSpinBox()
        self.threshold_upper.setRange(-3000, 3000)
        self.threshold_upper.setValue(3000)
        segmentation_form_layout.addRow("Lower threshold", self.threshold_lower)
        segmentation_form_layout.addRow("Upper threshold", self.threshold_upper)

        self.smoothing = qt.QDoubleSpinBox()
        self.smoothing.setRange(0, 1)
        self.smoothing.setDecimals(1)
        self.smoothing.setSingleStep(0.1)
        self.smoothing.setValue(0.5)
        segmentation_form_layout.addRow("Surface smoothing", self.smoothing)

        self.segmentation_status = qt.QLabel("no segmentation")
        segmentation_form_layout.addRow("Status", self.segmentation_status)     

        self.layout.addStretch(1)

        # Dialogs
        self.left_dialog = MeasurementsDialog('left', 
            slicer.modules.markups.logic().AddNewFiducialNode("BoneAngleMeterFiducialsLeft"), self)
        self.left_dialog.finished.connect(self.onDialogClose)
        self.right_dialog = MeasurementsDialog('right', 
            slicer.modules.markups.logic().AddNewFiducialNode("BoneAngleMeterFiducialsRight"), self)
        self.right_dialog.finished.connect(self.onDialogClose)
        
    def cleanup(self):
        pass

    def onDialogClose(self):
        self.left_button.setEnabled(True)
        self.right_button.setEnabled(True)

    def onLeftDialogButton(self):
        self.left_dialog.show()
        self.left_button.setEnabled(False)
        self.right_button.setEnabled(False)

    def onRightDialogButton(self):
        self.right_dialog.show()
        self.left_button.setEnabled(False)
        self.right_button.setEnabled(False)

    def onApplySegmentation(self):
        self.segmentation_status.setText("working...")

        # Get volume data
        volume_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        if len(volume_nodes) == 0:
            self.segmentation_status.setText("No data found")
            return
        if len(volume_nodes) > 1:
            self.segmentation_status.setText("Multiple volumes found. Only one volume is supported currently.")
            return
        volume_node = volume_nodes[0]

        # Create segmentation
        segmentation_node = slicer.mrmlScene.GetNodeByID(self.SEGMENTATION_NODE_NAME)
        if segmentation_node is not None:
            slicer.mrmlScene.RemoveNode(segmentation_node)
        segmentation_node = slicer.mrmlScene.AddNewNodeByClassWithID("vtkMRMLSegmentationNode", "", self.SEGMENTATION_NODE_NAME)
        segmentation_node.CreateDefaultDisplayNodes() # only needed for display
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(volume_node)
        segmentation_node.SetName(self.SEGMENTATION_NODE_NAME)
        segment_id = segmentation_node.GetSegmentation().AddEmptySegment("Bones")

        # Create segment editor to get access to effects
        segment_editor_widget = slicer.qMRMLSegmentEditorWidget()
        segment_editor_widget.setMRMLScene(slicer.mrmlScene)
        segment_editor_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segment_editor_widget.setMRMLSegmentEditorNode(segment_editor_node)
        segment_editor_widget.setSegmentationNode(segmentation_node)
        segment_editor_widget.setCurrentSegmentID(segment_id)
        segment_editor_widget.setMasterVolumeNode(volume_node)

        # Thresholding
        segment_editor_widget.setActiveEffectByName("Threshold")
        effect = segment_editor_widget.activeEffect()
        effect.setParameter("MinimumThreshold", f"{self.threshold_lower.value}")
        effect.setParameter("MaximumThreshold", f"{self.threshold_upper.value}")
        effect.self().onApply()

        # Clean up
        segment_editor_widget = None
        slicer.mrmlScene.RemoveNode(segment_editor_node)

        # Smoothing
        segmentation_node.GetSegmentation().SetConversionParameter("Smoothing factor",f"{self.smoothing.value}")

        # Make segmentation results visible in 3D
        segmentation_node.CreateClosedSurfaceRepresentation()

        # Center the 3d View on the scene
        layout_manager = slicer.app.layoutManager()
        three_d_Widget = layout_manager.threeDWidget(0)
        three_d_view = three_d_Widget.threeDView()
        three_d_view.resetFocalPoint()

        # Make segmentation invisible in sliced and set colors
        segmentation_node.GetDisplayNode().SetAllSegmentsVisibility2DOutline(False)
        segmentation_node.GetDisplayNode().SetAllSegmentsVisibility2DFill(False)
        segmentation_node.GetSegmentation().GetSegment(segment_id).SetColor(241/255, 241/255, 145/255)

        self.segmentation_status.setText("ok")

class MeasurementsDialog(qt.QDialog):
    '''
    Dialog containing basically all GUI items. Contains a stack of measurements
    '''
    def __init__(self, side, markup_node_id, base_widget):
        super().__init__()

        self.markup_node_id = markup_node_id
        self.base_widget = base_widget

        if side.lower() == 'left':
            self.side = 'left'
        elif side.lower() == 'right':
            self.side = 'right'
        else:
            raise ValueError(f"side should be eigher 'left' or 'right'. Found '{side}'.")

        self.setWindowTitle(f"Measurements - {self.side.upper()}")
        self.setWindowFlags(qt.Qt.WindowStaysOnTopHint)
        
        self.import_landmarks_button = qt.QPushButton(f"Import {self.side} landmarks")
        self.import_landmarks_button.clicked.connect(self._import_landmarks)
        self.import_landmarks_button.setDefault(False)
        self.import_landmarks_button.setAutoDefault(False)
        self.export_landmarks_button = qt.QPushButton(f"Export {self.side} landmarks")
        self.export_landmarks_button.clicked.connect(self._export_landmarks)
        self.export_landmarks_button.setDefault(False)
        self.export_landmarks_button.setAutoDefault(False)
        self.export_measurements_button = qt.QPushButton(f"Export {self.side} measurements")
        self.export_measurements_button.clicked.connect(self._export_measurements)
        self.export_measurements_button.setDefault(False)
        self.export_measurements_button.setAutoDefault(False)

        self.measurement_list = qt.QListWidget(self)
        self.measurement_stack = qt.QStackedWidget(self)
        self.measurement_list.currentRowChanged.connect(self._change_row)

        # Create deep-copy of all landmarks for this side
        self.landmarks = deepcopy(LANDMARKS)
        for landmark in self.landmarks:
            landmark.set_markups_node_id(self.markup_node_id)

        # Create all measurements
        for measurement in MEASUREMENTS:
            m = measurement()
            m.set_side(self.side)
            m.register_landmarks(self.landmarks)
            self.measurement_stack.addWidget(MeasurementWidget(m))
            self.measurement_list.addItem(m.name)
        
        left_sublayout = qt.QGridLayout()
        left_sublayout.addWidget(self.measurement_list, 0, 0, 1, 2)
        left_sublayout.addWidget(self.import_landmarks_button, 1, 0)
        left_sublayout.addWidget(self.export_landmarks_button, 1, 1)
        left_sublayout.addWidget(self.export_measurements_button, 2, 0, 1,)

        layout = qt.QHBoxLayout()
        layout.addLayout(left_sublayout)
        layout.addWidget(self.measurement_stack)

        self.setLayout(layout)

    def _export_landmarks(self):
        file_name = qt.QFileDialog.getSaveFileName(self, 'Export landmarks', '',"CSV File (*.csv)")
        if file_name == "": 
            return
        with open(file_name, 'w+', newline='') as csvfile:
            fieldnames = ['landmark name', 'x', 'y', 'z']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';' 
                                    if locale.localeconv()['decimal_point'] == "," else ",", quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for landmark in self.landmarks:
                if landmark.placed:
                    position = landmark.get_position()
                    writer.writerow({"landmark name": landmark.name, 
                                     "x": locale.str(position[0]), 
                                     "y": locale.str(position[1]), 
                                     "z": locale.str(position[2])})


    def _import_landmarks(self):
        file_name = qt.QFileDialog.getOpenFileName(self, 'Import landmarks', '',"CSV File (*.csv)")
        if file_name == "":
            return
        landmark_dict = {lm.name: lm for lm in self.landmarks}
        with open(file_name, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                try:
                    name = row['landmark name']
                    x = locale.atof(row['x'])
                    y = locale.atof(row['y'])
                    z = locale.atof(row['z'])
                except Exception as e:
                    errorDisplay("Invalid file. Must contain columns: 'landmark name', 'x', 'y', 'z'")
                    return
                if name not in landmark_dict.keys():
                    errorDisplay(f"Unknown landmark {name}")
                    return
                landmark_dict[name].define(x, y, z)
        # force update
        self.measurement_stack.currentWidget().disable() 
        self.measurement_stack.currentWidget().enable()

    def _export_measurements(self):
        file_name = qt.QFileDialog.getSaveFileName(self, 'Export measurements', '',"CSV File (*.csv)")
        if file_name == "":
            return

        with open(file_name, 'w+', newline='') as csvfile:
            fieldnames = ['measurement', 'value', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';' 
                                    if locale.localeconv()['decimal_point'] == "," else ",", quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for i in range(self.measurement_stack.count):
                measurement = self.measurement_stack.widget(i).measurement
                result_ready, result_value, result_string = measurement()
                if result_ready:
                    writer.writerow({"measurement": measurement.name, 
                                     "value": locale.str(result_value), 
                                     "description": result_string})
        

    def _change_row(self, i):
        self.measurement_stack.currentWidget().disable()
        self.measurement_stack.setCurrentIndex(i)
        self.measurement_stack.currentWidget().enable()

    # Override default events
    def showEvent(self, event):
        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActivePlaceNodeID(self.markup_node_id)

        # Auto-select first item
        if self.measurement_list.currentRow == -1 and self.measurement_list.count > 0:
            self.measurement_list.setCurrentRow(0)

        self.measurement_stack.currentWidget().enable()
        event.accept()

    def closeEvent(self, event):
        self.measurement_stack.currentWidget().disable()
        event.accept()
        self.accept() # set result code and emit finished signal


class MeasurementWidget(qt.QWidget):
    '''
    Widget that displays the landmarks and results of a measurement
    '''
    def __init__(self, measurement):
        super().__init__()

        self.measurement = measurement
        self.enabled = False

        self.landmark_stack = qt.QStackedWidget(self)
        self.landmark_list = qt.QListWidget()
        self.next_landmark_button = qt.QPushButton("Next")
        self.prev_landmark_button = qt.QPushButton("Previous")
        self.next_landmark_button.setDefault(True)
        self.next_landmark_button.setAutoDefault(False)
        self.prev_landmark_button.setDefault(False)
        self.prev_landmark_button.setAutoDefault(False)

        self.landmark_group_box = qt.QGroupBox("Landmarks")
        self.landmark_grid = qt.QGridLayout()
        self.landmark_grid.setColumnStretch(2, 1)
        self.landmark_grid.addWidget(self.landmark_list, 0, 0, 1, 2)
        self.landmark_grid.addWidget(self.prev_landmark_button, 1, 0)
        self.landmark_grid.addWidget(self.next_landmark_button, 1, 1)
        self.landmark_grid.addWidget(self.landmark_stack, 0, 2, 2, 1)
        self.landmark_group_box.setLayout(self.landmark_grid)

        self.name_label = qt.QLabel(f"<big>{self.measurement.name}</big>")
        self.name_label.setWordWrap(True)
        self.description_label = qt.QLabel(self.measurement.description)
        self.description_label.setWordWrap(True)
        self.measurement_label = qt.QLabel(f"Not available")
        
        layout = qt.QFormLayout()
        layout.addRow(self.name_label)
        layout.addRow("<b>Description</b>", self.description_label)
        layout.addRow("<b>Result</b>", self.measurement_label)
        layout.addRow(self.landmark_group_box)

        self.setLayout(layout)

        self.next_shortcut = qt.QShortcut(qt.QKeySequence('Return'), self)
        self.next_shortcut.activated.connect(self._next_row)
        self.next_shortcut.setContext(qt.Qt.ApplicationShortcut)

        self.prev_shortcut = qt.QShortcut(qt.QKeySequence('Shift+Return'), self)
        self.prev_shortcut.activated.connect(self._prev_row)
        self.prev_shortcut.setContext(qt.Qt.ApplicationShortcut)

        for landmark in self.measurement.get_landmarks():
            self.landmark_stack.addWidget(LandmarkWidget(landmark))
            self.landmark_list.addItem(landmark.name)
            landmark.add_change_callback(self.update_measurement)

        self.landmark_list.currentRowChanged.connect(self._change_row)
        self.next_landmark_button.clicked.connect(self._next_row)
        self.prev_landmark_button.clicked.connect(self._prev_row)

        self.update_measurement()

    def enable(self):
        # Auto-select first item
        if self.landmark_list.currentRow == -1 and self.landmark_list.count > 0:
            # Emit signal currentRowChanged
            self.landmark_list.setCurrentRow(0)

        for landmark in self.measurement.landmarks:
            landmark.show()
        
        current_landmark_widget = self.landmark_stack.currentWidget()
        current_landmark_widget.landmark.start_interaction()
                   
        self.next_shortcut.setEnabled(True)
        self.prev_shortcut.setEnabled(True)
        self.enabled = True

        self.update_measurement()
        
    def disable(self):
        for landmark in self.measurement.landmarks:
            landmark.stop_interaction()
            landmark.hide()
        self.next_shortcut.setEnabled(False)
        self.prev_shortcut.setEnabled(False)
        self.enabled = False

    def update_measurement(self):
        if self.enabled:
            try:
                result_ready, result_value, result_string = self.measurement()
                if result_ready:
                    self.measurement_label.setText(f"{result_value:.2f}\N{DEGREE SIGN} {result_string}")
                    self.measurement_label.setStyleSheet("QLabel { background-color : green}")
                else:
                    self.measurement_label.setText(result_string)
                    self.measurement_label.setStyleSheet("QLabel { background-color : orange}")
            except Exception as e:
                self.measurement_label.setText(f"Error executing measurement: {e}")
                self.measurement_label.setStyleSheet("QLabel { background-color : red}")

    # Internal callbacks
    def _next_row(self):
        if self.landmark_list.currentRow + 1 < self.landmark_list.count:
            # Emit signal currentRowChanged
            self.landmark_list.setCurrentRow(self.landmark_list.currentRow + 1)

    def _prev_row(self):
        if self.landmark_list.currentRow > 0:
            # Emit signal currentRowChanged
            self.landmark_list.setCurrentRow(self.landmark_list.currentRow - 1)

    def _change_row(self, i):
        old_landmark_widget = self.landmark_stack.currentWidget()
        old_landmark_widget.landmark.stop_interaction()
        self.landmark_stack.setCurrentIndex(i)
        new_landmark_widget = self.landmark_stack.currentWidget()
        new_landmark_widget.landmark.start_interaction()

class LandmarkWidget(qt.QWidget):
    '''
    Info-box for landmarks
    '''
    def __init__(self, landmark):
        super(LandmarkWidget, self).__init__()

        self.landmark = landmark

        self.landmark_label = qt.QLabel(f"<big>{self.landmark.name}</big>")
        self.landmark_label.setWordWrap(True)
        self.description_label = qt.QLabel(self.landmark.description)
        self.description_label.setWordWrap(True)
        if self.landmark.image_path != "":
            path = osp.join(MODULE_PATH, self.landmark.image_path)
            pixmap = qt.QPixmap(path)
            if pixmap.isNull():
                raise ValueError(f"Could not load image from file '{path}'")
            self.image = ResizableImage(pixmap)
        else:
            self.image = None

        layout = qt.QVBoxLayout()
        layout.addWidget(self.landmark_label)
        layout.addWidget(self.description_label)
        if self.image is not None:
            layout.addWidget(self.image)
            layout.setStretch(layout.count()-1, 1)
        self.setLayout(layout)


class ResizableImage(qt.QLabel):
    """
    Widget that displays an image and keeps the aspect ratio when rescaled.
    Inspired by:
    https://stackoverflow.com/questions/8211982/qt-resizing-a-qlabel-containing-a-qpixmap-while-keeping-its-aspect-ratio/
    """
    def __init__(self, pixmap) -> None:
        super().__init__()
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self.raw_pixmap = pixmap
        self.setPixmap(self.scaledPixmap())

    def heightForWidth(self, width):
        return self.pixmap.height() * width / self.pixmap.width()

    def sizeHint(self):
        w = self.width
        return qt.QSize(w, self.heightForWidth(w))

    def scaledPixmap(self):
        return self.raw_pixmap.scaled(self.size, qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)

    def resizeEvent(self, event):
        self.setPixmap(self.scaledPixmap())
        event.accept()