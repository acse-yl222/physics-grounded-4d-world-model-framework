import unittest,math
from pathlib import Path
import numpy as np
import torch
from urban_flow.solvers.actuator_line import FaceKernel,reference_blade,section_force

class ActuatorLineTests(unittest.TestCase):
 def test_masked_kernel_reproduces_linear_velocity_force_moment_and_work(self):
  dtype=torch.float64;shape=(12,13,14);h=2.;origin=torch.tensor([-10.,-12.,-8.],dtype=dtype);points=torch.tensor([[1.7,1.2,2.3],[3.2,.4,3.7]],dtype=dtype)
  opened=torch.ones(shape,dtype=torch.bool);opened[4:6,5:7,4:6]=False
  z,y,x=torch.meshgrid(*[torch.arange(n,dtype=dtype) for n in shape],indexing='ij');coords=torch.stack((x+.5,y+.5,z+.5),-1)*h+origin
  force=torch.tensor([[1.,2.,3.],[-.4,3.,2.]],dtype=dtype)
  total=torch.zeros(3,dtype=dtype);moment=torch.zeros(3,dtype=dtype);grid_work=0.;point_work=0.
  for c in range(3):
   xyz=coords.clone();xyz[...,c]+=.5*h
   field=1+xyz[...,0]*.2-xyz[...,1]*.3+xyz[...,2]*.1
   kernel=FaceKernel(points,origin,h,shape,opened,c,2.5)
   sample=kernel.sample(field);expected=1+points[:,0]*.2-points[:,1]*.3+points[:,2]*.1
   torch.testing.assert_close(sample,expected,atol=1e-12,rtol=1e-12)
   spread=kernel.spread(force[:,c],shape);total[c]=spread.sum();direction=torch.zeros(3,dtype=dtype);direction[c]=1
   moment+=(torch.linalg.cross(xyz,direction.expand_as(xyz))*spread[...,None]).sum((0,1,2))
   grid_work+=(spread*field).sum();point_work+=(sample*force[:,c]).sum()
  torch.testing.assert_close(total,force.sum(0),atol=1e-12,rtol=1e-12)
  torch.testing.assert_close(moment,torch.linalg.cross(points,force).sum(0),atol=1e-11,rtol=1e-12)
  torch.testing.assert_close(grid_work,point_work,atol=1e-12,rtol=1e-12)
 def test_section_lift_perpendicular_drag_dissipative_and_torque_driving(self):
  n=torch.tensor([[1.,0.,0.]],dtype=torch.float64);et=torch.tensor([[0.,1.,0.]],dtype=torch.float64);w=10*n-50*et
  area=torch.ones(1,dtype=torch.float64);one=torch.ones_like(area);zero=torch.zeros_like(area)
  lift=section_force(w,n,et,area,zero,one,zero,1.225)
  drag=section_force(w,n,et,area,zero,zero,one,1.225)
  self.assertLess(abs(float((lift*w).sum())),1e-10);self.assertGreater(float(lift[0,1]),0);self.assertGreater(float((drag*w).sum()),0)
  body_velocity=50*et;u=w+body_velocity;both=lift+drag
  torch.testing.assert_close((both*u).sum(),(both*body_velocity).sum()+(drag*w).sum())
 def test_reference_inputs_cover_full_angle_range(self):
  blade,tables=reference_blade(Path(__file__).resolve().parents[1]/'project/windfarm/inputs/nrel5mw_actuator_line',16)
  self.assertEqual(len(blade['radius_fraction']),16);self.assertEqual(len(tables),8)
  self.assertAlmostEqual(float(blade['dr_fraction'].sum()),61.5/63.)
  for a in tables:self.assertTrue(np.isfinite(a).all());self.assertGreaterEqual(a[:,2].min(),0)

if __name__=='__main__':unittest.main()

class RotatingFarmTests(unittest.TestCase):
 def test_three_blade_periodicity_and_positive_aerodynamic_torque(self):
  from types import SimpleNamespace
  from urban_flow.solvers.actuator_line import RotatingFarm
  torch.set_num_threads(2)
  shape=(24,24,24);zero=torch.zeros(shape,dtype=torch.float64);mask=torch.ones(shape,dtype=torch.bool)
  mac=SimpleNamespace(vel=[zero+10,zero.clone(),zero.clone()],opened=lambda c:mask)
  m=SimpleNamespace(k=zero,h=8.,shape=shape,mac=mac,time=0.)
  g=dict(origin_xyz_m=[0,0,0],turbines=[dict(id='t',hub_xyz_m=[96,96,96],radius_m=30.,normal_xyz=[1,0,0])])
  c=dict(alm_elements=4,alm_tsr=7.,inlet_m_s=10.,alm_pitch_deg=0.,alm_sigma_cells=2**.5,rho_kg_m3=1.225)
  f=RotatingFarm(m,g,c,Path(__file__).resolve().parents[1]/'project/windfarm/inputs/nrel5mw_actuator_line')
  a,r=f.loads(time_s=0);audit=f.grid_audit(a);b,s=f.loads(time_s=2*math.pi/(3*float(f.omega[0])))
  self.assertGreater(r[0]['thrust_N'],0);self.assertGreater(r[0]['shaft_torque_Nm'],0)
  for x,y in zip(a,b):torch.testing.assert_close(x,y,atol=1e-11,rtol=1e-10)
  self.assertLess(audit['relative_global_moment_error'],1e-12);self.assertLess(audit['relative_work_error'],1e-12)
