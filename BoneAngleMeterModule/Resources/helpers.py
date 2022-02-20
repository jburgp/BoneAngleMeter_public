import numpy as np
import math

def vector_with_two_points(i,j):

    return (j-i)

def normalvector_of_three_points(k,l,m):

    return np.cross((l-k),(l-m))
def normalvector_of_two_vectors(plane_vector_1, plane_vector_2):

    return np.cross(plane_vector_1,plane_vector_2)

def project_vector_to_plane_from_normal(normal, vector):
    normal_component = np.dot(normal, vector)/(np.linalg.norm(normal)**2) * normal
    return (vector - normal_component) # in-plane component

def project_vector_to_plane_from_2_vectors(plane_vector_1, plane_vector_2, vector):
    normal = normalvector_of_two_vectors(plane_vector_1,plane_vector_2)
    return project_vector_to_plane_from_normal(normal, vector)


def angle(u,v):

    c = np.dot(u,v)
    d = np.linalg.norm(u)
    e = np.linalg.norm(v)
    return math.acos(c/(d*e))

def angle_in_plane_with_normal(normal, vector_a, vector_b):

    vec_a_proj = project_vector_to_plane_from_normal(normal, vector_a)
    vec_b_proj = project_vector_to_plane_from_normal(normal, vector_b)

    return (angle(vec_a_proj, vec_b_proj)*180/math.pi)

def angle_in_plane_from_two_vectors(plane_vector_1, plane_vector_2, vector_a, vector_b):
    vec_a_proj = project_vector_to_plane_from_2_vectors(plane_vector_1, plane_vector_2, vector_a)
    vec_b_proj = project_vector_to_plane_from_2_vectors(plane_vector_1, plane_vector_2, vector_b)
    normal=np.cross(plane_vector_1,plane_vector_2)

    return (angle(vec_a_proj, vec_b_proj)*180/math.pi)