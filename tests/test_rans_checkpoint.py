import tempfile
from pathlib import Path
import unittest
import torch
from urban_flow.solvers.rans.tunnel import Tunnel
from urban_flow.paper_rotor.run_torch_rans import save_checkpoint,restore_checkpoint


class CheckpointTests(unittest.TestCase):
    def tunnel(self,model):
        return Tunnel((6,6,12),(.1,.1,.1),10.,1.5e-5,.003,.03,model=model)

    def test_continuation_matches_uninterrupted_for_both_models(self):
        for model in ('kEpsilon','kOmegaSST','kOmegaSSTLF18'):
            with self.subTest(model=model),tempfile.TemporaryDirectory() as directory:
                original=self.tunnel(model)
                for _ in range(3):original.advance(.0001)
                save_checkpoint(original,Path(directory),model)
                resumed=self.tunnel(model)
                restore_checkpoint(resumed,Path(directory)/'checkpoint.pt')
                for _ in range(3):
                    original.advance(.0001);resumed.advance(.0001)
                self.assertEqual(original.time,resumed.time)
                for a,b in zip(original.faces+[original.k,original.epsilon,original.omega],
                               resumed.faces+[resumed.k,resumed.epsilon,resumed.omega]):
                    torch.testing.assert_close(a,b,rtol=0,atol=0)

    def test_bad_checkpoint_rejected_without_changing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            solver=self.tunnel('kOmegaSST');out=Path(directory)
            save_checkpoint(solver,out,solver.model)
            state=torch.load(out/'checkpoint.pt',weights_only=True)
            state['omega'][0,0,0]=-1
            torch.save(state,out/'bad.pt')
            before=solver.omega.clone()
            with self.assertRaises(ValueError):restore_checkpoint(solver,out/'bad.pt')
            torch.testing.assert_close(before,solver.omega)


if __name__=='__main__':unittest.main()
