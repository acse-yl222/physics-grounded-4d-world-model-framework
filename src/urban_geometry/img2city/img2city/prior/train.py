"""img2city/prior/train.py -- train a small image->parameters regressor on the synthetic dataset.

  pip install torch torchvision pillow pandas        # once
  python -m img2city.prior.train --data data/prior/dataset --epochs 40 --out data/prior/param_model.pt

A ResNet18 backbone (ImageNet-pretrained) with a small regression head predicts the
N_PARAMS building parameters, normalised to [0,1]. Trains fine on one GPU / Apple-Silicon
MPS / Colab in well under an hour for a few thousand images. Saves weights + the param
ranges so predict.py can denormalise.
"""
import os
import argparse
import csv
from img2city import config
from img2city.prior import params as P

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from torchvision import models
from PIL import Image


class BuildingDS(Dataset):
    def __init__(self, csv_path, train=True):
        self.rows = []
        with open(csv_path) as f:
            r = csv.reader(f)
            self.header = next(r)
            for row in r:
                self.rows.append(row)
        aug = [T.ColorJitter(0.2, 0.2, 0.2)] if train else []
        self.tf = T.Compose([T.Resize((224, 224))] + aug +
                            [T.ToTensor(),
                             T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        row = self.rows[i]
        img = Image.open(row[0]).convert("RGB")
        x = self.tf(img)
        raw = [float(v) for v in row[1:]]
        y = torch.tensor(P.normalize(raw), dtype=torch.float32)
        return x, y


def make_model():
    m = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    m.fc = nn.Sequential(nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.2),
                         nn.Linear(256, P.N_PARAMS), nn.Sigmoid())
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(config.PRIOR_DIR / "dataset"))
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--out", default=str(config.PRIOR_DIR / "param_model.pt"))
    a = ap.parse_args()

    dev = ("cuda" if torch.cuda.is_available()
           else "mps" if torch.backends.mps.is_available() else "cpu")
    print("device:", dev)

    lp = os.path.join(a.data, "labels.csv")
    if (not os.path.exists(lp)) or sum(1 for _ in open(lp)) < 3:
        raise SystemExit(
            "No dataset yet at %s.\nRun  python -m img2city.prior.gen_dataset --n 1500  FIRST and let it\n"
            "finish (or Ctrl-C it once it has a few hundred samples), THEN run train.py." % lp)
    ds = BuildingDS(lp, train=True)
    n_val = max(1, len(ds) // 10)
    tr, va = torch.utils.data.random_split(ds, [len(ds) - n_val, n_val],
                                           generator=torch.Generator().manual_seed(0))
    dl_tr = DataLoader(tr, batch_size=a.bs, shuffle=True, num_workers=2)
    dl_va = DataLoader(va, batch_size=a.bs, num_workers=2)

    model = make_model().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr)
    lossf = nn.SmoothL1Loss()

    best = 1e9
    for ep in range(a.epochs):
        model.train()
        for x, y in dl_tr:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad(); loss = lossf(model(x), y); loss.backward(); opt.step()
        model.eval(); vl = 0.0; nb = 0
        with torch.no_grad():
            for x, y in dl_va:
                x, y = x.to(dev), y.to(dev)
                vl += lossf(model(x), y).item(); nb += 1
        vl /= max(1, nb)
        print("epoch %2d  val_loss %.4f" % (ep, vl), flush=True)
        if vl < best:
            best = vl
            torch.save({"state_dict": model.state_dict(),
                        "param_ranges": P.PARAM_RANGES}, a.out)
    print("saved best (val_loss %.4f) -> %s" % (best, a.out))


if __name__ == "__main__":
    main()
