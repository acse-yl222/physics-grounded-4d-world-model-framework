import json,tempfile,unittest
from pathlib import Path
import numpy as np
from urban_flow.paper_rotor.sample_foam_alignment import sample

class SamplingTests(unittest.TestCase):
    def test_linear_field_and_permuted_cell_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);case=root/'case';(case/'10').mkdir(parents=True)
            cfg={'grid_cells_xyz':[20,12,6],'actual_spacing_xyz_m':[1,1,1],'hub_xyz_m':[2.2,6,3],'rotor_diameter_m':1,'inlet_m_s':10}
            (case/'configuration.json').write_text(json.dumps(cfg))
            z,y,x=np.meshgrid(np.arange(6)+.5,np.arange(12)+.5,np.arange(20)+.5,indexing='ij')
            c=np.column_stack([x.ravel(),y.ravel(),z.ravel()]);order=np.random.default_rng(1).permutation(len(c));c=c[order]
            u=np.column_stack([2*c[:,0]+3*c[:,1]+c[:,2],np.zeros(len(c)),np.zeros(len(c))])
            for name,a in [('C',c),('U',u)]:
                (case/'10'/name).write_text('internalField nonuniform List<vector>\n'+str(len(a))+'\n(\n'+'\n'.join('('+ ' '.join(map(str,r))+')' for r in a)+'\n)\n;')
            out=sample(case,10,root/'out')
            for d in [1,3,5]:
                a=json.loads((out/f'wake_{d}d.json').read_text());p=np.array(a['positions'])
                np.testing.assert_allclose(a['values'],1-(2*p[:,0]+3*p[:,1]+p[:,2])/10,atol=1e-12)
