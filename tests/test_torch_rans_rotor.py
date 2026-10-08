import unittest
from urban_flow.paper_rotor.torch_rans import RotorTunnel


class RotorCouplingTests(unittest.TestCase):
    def check_rotor(self,model):
        config=dict(mesh_counts_xyz=[32,16,16],domain_xyz_m=[3.2,1.6,1.6],
            inlet_m_s=10.,kinematic_viscosity_m2_s=1.5e-5,turbulence_intensity=.003,
            turbulence_length_m=.03,rotor_diameter_m=.8,inner_diameter_m=.09,
            rotor_thickness_m=.4,sigma_m=.1,cutoff_sigma=2.,ct=.75,rho_kg_m3=1.225,
            hub_xyz_m=[1.,.8,.8])
        solver=RotorTunnel(config,model=model)
        initial=float(solver.rotor_load()['disc_speed'])
        for _ in range(8):
            result=solver.advance_rotor(min(.001,solver.stable_dt()))
        self.assertLess(float(solver.rotor_load()['disc_speed']),initial)
        self.assertLess(result['force_balance_error_N'],1e-10)
        self.assertLess(result['divergence_rms'],1e-10)

    def test_kepsilon_rotor(self):self.check_rotor('kEpsilon')

    def test_sst_rotor(self):self.check_rotor('kOmegaSST')

    def test_lf18_rotor(self):self.check_rotor('kOmegaSSTLF18')


if __name__=='__main__':unittest.main()
