import numpy as np
import os.path as osp
import slicer

class SimpleLandmark:
    def __init__(self, name, description="", image_path=""):
        self.name = name
        self.placed = False
        self.change_callbacks = []
        self.description = description
        self.image_path = image_path

        # Internal members
        self._markups_node = None
        self._id = None
        self._private_observers = []

    def set_markups_node_id(self, id):
        self._markups_node = slicer.mrmlScene.GetNodeByID(id)

        # Set automatic glyph style
        self._markups_node.GetDisplayNode().SetGlyphType(self._markups_node.GetDisplayNode().ThickCross2D)
        self._markups_node.GetDisplayNode().SetGlyphScale(2.5)

    def add_change_callback(self, callback):
        self.change_callbacks.append(callback)

    def show(self):
        if self._id is not None:
            self._markups_node.SetNthFiducialVisibility(self._id, True)

    def hide(self):
        self.stop_interaction()
        if self._id is not None:
            self._markups_node.SetNthFiducialVisibility(self._id, False)

    def start_interaction(self):
        if self.placed:
            self._markups_node.SetNthFiducialLocked(self._id, False)
            self._markups_node.SetNthFiducialSelected(self._id, True)
            self.center_in_slices()
            self._private_observers.append(self._markups_node.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, 
                                                                         lambda caller, event: self._changed_callback(caller)))
        else:
            slicer.modules.markups.logic().StartPlaceMode(0)
            self._private_observers.append(self._markups_node.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, 
                                                                         lambda caller, event: self._added_callback()))
            self._private_observers.append(self._markups_node.AddObserver(slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, 
                                                                         lambda caller, event: self._defined_callback()))

    def stop_interaction(self):
        if self.placed:
            self._markups_node.SetNthFiducialLocked(self._id, True)
            self._markups_node.SetNthFiducialSelected(self._id, False)
        
        # Turn off placement mode and remove observers
        for observer in self._private_observers:
            self._markups_node.RemoveObserver(observer)

        interaction_node = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        interaction_node.SwitchToViewTransformMode()
        interaction_node.SetPlaceModePersistence(0)                                                       

    def center_in_slices(self, excluded_slice_nodes=None):
        position_RAS = [0.0, 0.0, 0.0]
        self._markups_node.GetNthFiducialPosition(self._id, position_RAS)

        if excluded_slice_nodes is None:
            slicer.vtkMRMLSliceNode.JumpAllSlices(slicer.mrmlScene, *position_RAS, slicer.vtkMRMLSliceNode.CenteredJumpSlice)
        else:
            slice_nodes = slicer.util.getNodesByClass("vtkMRMLSliceNode")
            for slice_node in slice_nodes:
                if slice_node.GetName() not in excluded_slice_nodes:
                    slice_node.SetJumpModeToCentered()
                    slice_node.JumpSlice(*position_RAS)

    def define(self, x, y, z):
        self._markups_node.AddFiducial(x, y, z, self.name)
        self._id = self._markups_node.GetNumberOfFiducials() - 1
        self.placed = True
        self._changed_callback()

    def get_position(self):
        if self._id is None or not self.placed:
            return None
        xyz_buffer = [0.0, 0.0, 0.0]
        self._markups_node.GetNthFiducialPosition(self._id, xyz_buffer)
        return np.array(xyz_buffer)

    def _added_callback(self):
        '''
        Called when a point is added (but not necessarily placed). Takes care of giving the right label to the newly added point
        '''
        id = self._markups_node.GetNumberOfFiducials() - 1 # id is only temporary until the point is defined
        self._markups_node.SetNthFiducialLabel(id, self.name)
        
    def _defined_callback(self):
        '''
        Called when a point is placed/defined. 
        '''
        self._id = self._markups_node.GetNumberOfFiducials()-1
        self.placed = True
        self.stop_interaction()
        self._changed_callback()
        self.start_interaction()

    def _changed_callback(self, caller=None):
        '''
        Called when a point is changed (including defined). Triggers updates to all dependent measurements
        '''
        if caller is not None:
            calling_node = caller.GetAttribute("Markups.MovingInSliceView")
        else:
            calling_node = None
        self.center_in_slices([calling_node])

        for cb in self.change_callbacks:
            cb()

