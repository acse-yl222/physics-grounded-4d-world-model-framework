import json,numpy as np
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/one-bank-photo-study-003';im=Image.open(R/'references/pexels-ollie-craig-11491155.jpeg');im.thumbnail((1921,1280));fig,ax=plt.subplots(figsize=(13,9));ax.imshow(im);d=json.loads(Path('cache/onebank_curve.json').read_text());xy=np.array(d['pixels']);ax.plot(xy[:,0],xy[:,1],'o-',c='yellow',lw=1);ax.text(1450,360,'One Bank Street / 207561\nSouth-west edge samples; north edge occluded',color='yellow',fontsize=9);ax.set_xlim(1400,1850);ax.set_ylim(940,340);fig.savefig(R/'references/one_bank_photo_silhouette003.png',dpi=150)
render=Image.open(O/'matched-camera.png');fig,axs=plt.subplots(1,2,figsize=(12,8));axs[0].imshow(im);axs[1].imshow(render)
for ax in axs:ax.set_xlim(1450,1820);ax.set_ylim(930,350)
axs[0].set_title('Licensed photo, actual visible west');axs[1].set_title('Estimated model, same fitted camera');fig.savefig(R/'references/one_bank_photo_comparison003.png',dpi=150)
