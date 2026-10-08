import unittest
import numpy as np
from urban_planning.large_domain import block_map,edited,height,BASE
class LargeDomainTests(unittest.TestCase):
 def test_edit_window_is_16_blocks_and_keeps_buffer_fixed(self):
  blocks=block_map((1024,1024))
  self.assertEqual(set(np.unique(blocks)),set(range(16))|{-1})
  self.assertTrue(all(np.count_nonzero(blocks==i)==4096 for i in range(16)))
  self.assertEqual(blocks[400,400],0);self.assertEqual(blocks[655,655],15)
 def test_edits_preserve_other_buildings_and_ground(self):
  solid=np.zeros((8,4,4),bool);solid[0]=True;solid[:4,1,1]=True;solid[:3,2,2]=True
  blocks=np.full((4,4),-1);blocks[1,1]=0
  plan={'height_steps':[1]+[0]*15,'cool_blocks':[]}
  result=edited(solid,plan,blocks)
  self.assertEqual(height(result)[1,1],20)
  self.assertTrue(np.array_equal(result[:,2,2],solid[:,2,2]))
  self.assertTrue(result[0].all());self.assertEqual(height(result)[0,0],0)
 def test_baseline_preserves_source_voxels(self):
  solid=np.zeros((8,4,4),bool);solid[0]=True;solid[3,1,1]=True
  self.assertTrue(np.array_equal(edited(solid,BASE,np.zeros((4,4))),solid))
if __name__=='__main__':unittest.main()
