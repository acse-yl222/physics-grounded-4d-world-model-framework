import unittest
import numpy as np
from visualization.adapters.img2city_legacy import campus_to_region_affine

class LegacyCoordinates(unittest.TestCase):
    def test_matches_original_assembly_frame(self):
        matrix,offset=campus_to_region_affine()
        np.testing.assert_allclose(offset,[710.3555784760871,-211.57687438176112],atol=1e-9)
        points=np.array([[0,0],[173.3,-481.3],[-124,-784],[572,-68.]])
        region=points@matrix.T+offset
        A=np.array([[.9971372878088512,.03850621238135248],[-.03860679068166115,.9997417959287375]])
        campus=region@A.T+np.array([-700.1750108416061,238.94679349918735])
        np.testing.assert_allclose(campus,points*np.array([1,111320/110540]),atol=1e-9)

    def test_gltf_axis_handedness_and_height(self):
        matrix,offset=campus_to_region_affine()
        M=np.eye(4);M[0,0]=matrix[0,0];M[0,2]=-matrix[0,1];M[2,0]=-matrix[1,0];M[2,2]=matrix[1,1];M[0,3]=offset[0];M[2,3]=-offset[1]
        point=np.array([173.,12.,481.,1.]);world=M@point
        np.testing.assert_allclose(world[[0,2]],(matrix@np.array([173.,-481.])+offset)*[1,-1])
        self.assertEqual(world[1],12)
        self.assertGreater(np.linalg.det(M),0)
