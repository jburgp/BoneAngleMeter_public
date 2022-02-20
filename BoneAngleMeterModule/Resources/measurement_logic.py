import math
import numpy as np
from scipy.optimize import least_squares


from Resources.helpers import *

class BaseMeasurement:
    '''
    Base class for all measurements. Child classes need to implement the _measure method that takes a
    dictionary of landmark positions and returns a float value and a string description. Calls to the
    measurement should be done via ().
    '''
    def __init__(self, name):
        self.name = name
        self.side = None
        self.landmarks = []
        self.description = ""

    def set_side(self, side):
        self.side = side

    def register_landmarks(self, landmarks):
        # Hacky way to find all used landmark names
        class FakeDict:
            def __init__(self):
                self.queried_keys = []

            def __getitem__(self, key):
                self.queried_keys.append(key)
                return np.random.rand(3)

        fake_dict = FakeDict()
        self._measure(fake_dict)
        used_landmark_names = fake_dict.queried_keys

        # Register landmark objects
        for name in used_landmark_names:
            landmark_found = False
            for landmark in landmarks:
                if landmark.name == name:
                    self.landmarks.append(landmark)
                    landmark_found = True
                    break
            if not landmark_found:
                raise ValueError(f"Could not register landmark with name {name}")

        # Register update callback for all landmarks
        for landmark in self.landmarks:
            landmark.add_change_callback(self.maybe_update)

    def get_landmarks(self):
        return self.landmarks

    def maybe_update(self):
        pass

    def __call__(self):
        # Check if all landmarks were placed
        for landmark in self.landmarks:
            if not landmark.placed:
                return False, None, "Not all landmarks defined"
        point_dict = {l.name: l.get_position() for l in self.landmarks}
        angle, message = self._measure(point_dict)
        return True, angle, message

class TibiaTorsionMeasurement(BaseMeasurement):
    def __init__(self):
        super().__init__('Tibia Torsion')
    
    def _measure(self, point_dict):
        normal = vector_with_two_points(point_dict["distal tibia midpoint"], point_dict["proximal tibia midpoint"])
        vector_distal = vector_with_two_points(point_dict["medial cochlea"], point_dict["lateral cochlea"])
        vector_proximal = vector_with_two_points(point_dict["condylus medialis tibiae"], point_dict["condylus lateralis tibiae"])
        
        vector_distal_proj = project_vector_to_plane_from_normal(normal, vector_distal)
        vector_proximal_proj = project_vector_to_plane_from_normal(normal, vector_proximal)
        
        a = angle(vector_distal_proj, vector_proximal_proj)*180/math.pi
        
        t = np.cross(vector_proximal_proj, vector_distal_proj)
        q = np.dot(t,normal)
        
        if self.side.lower() == "right":
            return a, "Innenrotation" if q > 0 else "Aussenrotation"
        elif self.side.lower() == "left":
            return a, "Aussenrotation" if q > 0 else "Innenrotation"
        else:
            raise ValueError(f"Unknown side {self.side}")

class VarusValgusTibiaMeasurement(BaseMeasurement):
    def __init__(self):
        super().__init__('Varus Valgus Tibia')
        self.description = "TEST"
    
    def _measure(self, point_dict):
        normal = np.cross((vector_with_two_points(point_dict["distal tibia midpoint"], point_dict["proximal tibia midpoint"])),(vector_with_two_points(point_dict["condylus medialis tibiae"], point_dict["condylus lateralis tibiae"])))
        vector_proximal_tibia_vv = vector_with_two_points(point_dict["lateral cochlea articulation point tibia"], point_dict["medial cochlea articulation point tibia"])
        vector_distal_tibia_vv = vector_with_two_points(point_dict["lateral condyle articulation point tibia"], point_dict["medial condyle articulation point tibia"])

        normal_component = np.dot(normal, vector_distal_tibia_vv)/(np.linalg.norm(normal)**2) * normal
        vector_proximal_tibia_vv_proj = project_vector_to_plane_from_normal(normal, vector_proximal_tibia_vv)
        vector_distal_tibia_vv_proj = project_vector_to_plane_from_normal(normal, vector_distal_tibia_vv)
        

        a = angle(vector_proximal_tibia_vv_proj, vector_distal_tibia_vv_proj)*180/math.pi
        
        t = np.cross(vector_proximal_tibia_vv_proj, vector_distal_tibia_vv_proj)
        q = np.dot(t,normal)
        if self.side.lower() == "right":
            return a, "Varus" if q > 0 else "Valgus"
        elif self.side.lower() == "left":
            return a, "Valgus" if q > 0 else "Varus"
        else:
            raise ValueError(f"Unknown side {self.side}")

class TibiotalarRotationMeasurement(BaseMeasurement):
    def __init__(self):
        super().__init__("Tibiotalar Rotation")
    
    def _measure(self, point_dict):
        normal = vector_with_two_points(point_dict["distal tibia midpoint"], point_dict["proximal tibia midpoint"])
        vector_distaltibia = vector_with_two_points(point_dict["medial cochlea"], point_dict["lateral cochlea"])
        vector_talus = vector_with_two_points(point_dict["medial talus"], point_dict["lateral talus"])
        
        vector_distaltibia_proj = project_vector_to_plane_from_normal(normal, vector_distaltibia)
        vector_talus_proj = project_vector_to_plane_from_normal(normal, vector_talus)
        
        
        a = angle(vector_distaltibia_proj, vector_talus_proj)*180/math.pi
        
        t = np.cross(vector_distaltibia_proj, vector_talus_proj)
        q = np.dot(t,normal)
        
        if self.side.lower() == "right":
            return a, "Innenrotation" if q > 0 else "Aussenrotation"
        elif self.side.lower() == "left":
            return a, "Aussenrotation" if q > 0 else "Innenrotation"
        else:
            raise ValueError(f"Unknown side {self.side}")

class FemorotibialRotationMeasurement(BaseMeasurement):
    def __init__(self):
        super().__init__("Femorotibial Rotation")

    def _measure(self, point_dict):
        normal = vector_with_two_points(point_dict["distal tibia midpoint"], point_dict["proximal tibia midpoint"])

        vector_distal_femur = vector_with_two_points(point_dict["medial femur condyle"], point_dict["lateral femur condyle"])
        vector_prox_tibia = vector_with_two_points(point_dict["condylus medialis tibiae"], point_dict["condylus lateralis tibiae"])
        
        vector_distal_femur_proj = project_vector_to_plane_from_normal(normal, vector_distal_femur)
        vector_prox_tibia_proj = project_vector_to_plane_from_normal(normal, vector_prox_tibia)
        
        a = angle(vector_distal_femur_proj, vector_prox_tibia_proj)*180/math.pi
        
        t = np.cross(vector_distal_femur_proj, vector_prox_tibia_proj)
        q = np.dot(t,normal)
        
        if self.side.lower() == "right":
            return a, "Innenrotation" if q > 0 else "Aussenrotation"
        elif self.side.lower() == "left":
            return a, "Aussenrotation" if q > 0 else "Innenrotation"
        else:
            raise ValueError(f"Unknown side {self.side}")

class VarusValgusFemurMeasurement(BaseMeasurement):
    def __init__(self):
        super().__init__("Varus Valgus Femur")

    def _measure(self, point_dict):
        normal = np.cross((vector_with_two_points(point_dict["proximal femur midpoint"], point_dict["distal femur midpoint"])), (vector_with_two_points(point_dict["medial femur condyle"], point_dict["lateral femur condyle"])))
        vector_axis_femur_vv = vector_with_two_points(point_dict["distal femur midpoint"], point_dict["proximal femur midpoint"])
        vector_dist_femur_vv =  vector_with_two_points(point_dict["medial femur condyle"], point_dict["lateral femur condyle"])
        
        vector_axis_femur_vv_proj = project_vector_to_plane_from_normal(normal, vector_axis_femur_vv)
        vector_dist_femur_vv_proj = project_vector_to_plane_from_normal(normal, vector_dist_femur_vv)
        
        a = angle(vector_axis_femur_vv_proj, vector_dist_femur_vv_proj)*180/math.pi -90
        
        t = np.cross(vector_axis_femur_vv_proj, vector_dist_femur_vv_proj)
        q = np.dot(t,normal)
        if self.side.lower() == "right":
            return a, "Varus" if q > 0 else "Valgus"
        elif self.side.lower() == "left":
            return a, "Valgus" if q > 0 else "Varus"
        else:
            raise ValueError(f"Unknown side {self.side}")

class AntetorsionMeasurement(BaseMeasurement):
    def __init__(self):
        super().__init__("Antetorsion")

    def center_of_femur_head(self, point_dict):   
        def fit_sphere_least_squares(x_values, y_values, z_values, initial_parameters, bounds=((-np.inf, -np.inf, -np.inf, -np.inf),(np.inf, np.inf, np.inf, np.inf))):
            return least_squares(_calculate_residual_sphere, initial_parameters, bounds=bounds, method="trf", jac="3-point", args=(x_values, y_values, z_values))

        def _calculate_residual_sphere(parameters, x_values, y_values, z_values):
            """
            Source: https://github.com/thompson318/scikit-surgery-sphere-fitting/blob/master/sksurgeryspherefitting/algorithms/sphere_fitting.py
            Calculates the residual error for an x,y,z coordinates, fitted
            to a sphere with centre and radius defined by the parameters tuple
            :return: The residual error
            :param: A tuple of the parameters to be optimised, should contain [x_centre, y_centre, z_centre, radius]
            :param: arrays containing the x,y, and z coordinates."""

            #extract the parameters
            x_centre, y_centre, z_centre, radius = parameters
            #use numpy's sqrt function here, which works by element on arrays
            distance_from_centre = np.sqrt((x_values - x_centre)**2 + (y_values - y_centre)**2 + (z_values - z_centre)**2)
            return distance_from_centre - radius

        # Fit a sphere to the markups fidicual points
        markups= [point_dict["point on femur head 1"], point_dict["point on femur head 2"], point_dict["point on femur head 3"], point_dict["point on femur head 4"], point_dict["point on femur head 5"]]
        markupsPositions = np.array(markups)
        # initial guess

        center0 = np.mean(markupsPositions, 0)
        radius0 = np.linalg.norm(np.amin(markupsPositions,0)-np.amax(markupsPositions,0))/2.0
        fittingResult = fit_sphere_least_squares(markupsPositions[:,0], markupsPositions[:,1], markupsPositions[:,2], [center0[0], center0[1], center0[2], radius0])
        [centerX, centerY, centerZ, radius] = fittingResult["x"]
        center0 = [centerX, centerY, centerZ]
        return center0


    
    def _measure(self, point_dict):
        center = self.center_of_femur_head(point_dict)
        normal = vector_with_two_points(point_dict["distal femur midpoint"], point_dict["proximal femur midpoint"])
        vector_distal_femur = vector_with_two_points(point_dict["medial femur condyle"], point_dict["lateral femur condyle"])
        vector_femur_neck = vector_with_two_points(center, point_dict["femur neck"])
        
        vector_distal_femur_proj = project_vector_to_plane_from_normal(normal, vector_distal_femur)
        vector_femur_neck_proj = project_vector_to_plane_from_normal(normal, vector_femur_neck)
        
        a = angle(vector_femur_neck_proj, vector_distal_femur_proj)*180/math.pi
        
        t = np.cross(vector_distal_femur_proj, vector_femur_neck_proj)
        q = np.dot(t,normal)
        
        if self.side.lower() == "right":
            return a, "no Antetorsion" if q > 0 else "Antetorsion"
        elif self.side.lower() == "left":
            return a, "Antetorsion" if q > 0 else "no Antetorsion"
        else:
            raise ValueError(f"Unknown side {self.side}")
        

class ExampleMeasurement(BaseMeasurement):
    '''
    This class SHOULD NOT BE USED, it is just provided as a example that shows how
    child classes should be implemented.
    '''
    def __init__(self, display_name):
        super().__init__(display_name)
    
    def _measure(self, point_dict):
        p = point_dict['landmark name'] # access landmarks
        m = 42 # calculate float measurement
        
        # Potentially return different descriptions for each side
        if self.side.lower() == "right":
            return m, "Some description"
        elif self.side.lower() == "left":
            return m, "Another description"
        else:
            raise ValueError(f"Unknown side {self.side}")

