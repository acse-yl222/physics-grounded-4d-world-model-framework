"""img2city/prior/predict.py -- image -> predicted building parameters -> build_building description.

  python -m img2city.prior.predict --image data/business_school/modelpic.jpeg --out data/prior/pred_desc.json

Then feed that description straight to the agent as iteration 0:

  python -m img2city.building.generate --data data/business_school --ref modelpic.jpeg --view aerial \
          --mode assemble --init-desc data/prior/pred_desc.json
"""
import os
import json
import argparse
from img2city import config
from img2city.prior import params as P

import torch
import torchvision.transforms as T
from PIL import Image
from img2city.prior.train import make_model


def predict(model_path, image_path):
    ckpt = torch.load(model_path, map_location="cpu")
    model = make_model()
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    tf = T.Compose([T.Resize((224, 224)), T.ToTensor(),
                    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    x = tf(Image.open(image_path).convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        nvec = model(x)[0].tolist()
    vec = P.denormalize(nvec)
    return P.vec_to_desc(vec), dict(zip(P.NAMES, vec))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(config.PRIOR_DIR / "param_model.pt"))
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", default=str(config.PRIOR_DIR / "pred_desc.json"))
    a = ap.parse_args()
    desc, named = predict(a.model, os.path.abspath(a.image))
    json.dump(desc, open(a.out, "w"), indent=2)
    print("predicted params:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in named.items()})
    print("description ->", a.out)


if __name__ == "__main__":
    main()
