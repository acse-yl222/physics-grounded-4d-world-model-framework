// Procedural facade, roof and ground textures drawn on canvases.
// Facade tiles cover 4 window bays horizontally and 2 storeys vertically so a
// wall UV of (distance / (4 * bay), height / (2 * storey)) aligns windows with floors.
import * as THREE from 'three';

const cache = new Map();

export function rng(seed) {
  let s = Math.floor(seed * 2 ** 31) || 1;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

export function canvasTexture(key, w, h, draw, { repeat = true, srgb = true } = {}) {
  if (cache.has(key)) return cache.get(key);
  const c = canvas(w, h);
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.name = key;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  cache.set(key, t);
  return t;
}

const hex = (c) => '#' + new THREE.Color(c).getHexString();
function shade(color, k) {
  const c = new THREE.Color(color);
  c.multiplyScalar(k);
  return hex(c);
}

function noise(g, w, h, base, amount, seed, size = 2) {
  const r = rng(seed);
  g.fillStyle = base;
  g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += size)
    for (let x = 0; x < w; x += size) {
      const k = 1 + (r() - 0.5) * amount;
      g.fillStyle = shade(base, k);
      g.fillRect(x, y, size, size);
    }
}

function bricks(g, x0, y0, w, h, base, mortar, seed, course = 4, len = 10) {
  const r = rng(seed);
  g.fillStyle = mortar;
  g.fillRect(x0, y0, w, h);
  for (let y = y0, row = 0; y < y0 + h; y += course, row++)
    for (let x = x0 - (row % 2 ? len / 2 : 0); x < x0 + w; x += len) {
      g.fillStyle = shade(base, 0.82 + r() * 0.36);
      g.fillRect(Math.max(x, x0) + 0.5, y + 0.5, len - 1, course - 1);
    }
}

// Window glass: sky reflection gradient with occasional lit or curtained panes.
function glass(g, x, y, w, h, r, tone = '#3c4d5c') {
  const grad = g.createLinearGradient(x, y, x + w * 0.4, y + h);
  grad.addColorStop(0, shade(tone, 1.55));
  grad.addColorStop(0.45, tone);
  grad.addColorStop(1, shade(tone, 0.7));
  g.fillStyle = grad;
  g.fillRect(x, y, w, h);
  const p = r();
  if (p < 0.18) {
    g.fillStyle = 'rgba(240,226,190,0.55)';
    g.fillRect(x + 1, y + h * 0.15, w - 2, h * 0.7);
  } else if (p < 0.4) {
    g.fillStyle = 'rgba(225,215,200,0.6)';
    g.fillRect(x, y, w * 0.28, h);
    g.fillRect(x + w * 0.72, y, w * 0.28, h);
  }
}

function sash(g, x, y, w, h, r, frame = '#f2efe8', tone) {
  glass(g, x, y, w, h, r, tone);
  g.strokeStyle = frame;
  g.lineWidth = Math.max(1.5, w * 0.07);
  g.strokeRect(x, y, w, h);
  g.beginPath();
  g.moveTo(x, y + h / 2);
  g.lineTo(x + w, y + h / 2);
  g.moveTo(x + w / 2, y);
  g.lineTo(x + w / 2, y + h);
  g.lineWidth = Math.max(1, w * 0.04);
  g.stroke();
}

// Facade styles. Each draw call receives (ctx, w, h, rng) for a 4-bay x 2-storey tile.
export const FACADES = {
  stucco: {
    colors: ['#efeae0', '#f3efe6', '#e9e1cf', '#eee6dd', '#f0e4d4'],
    draw(g, w, h, r, color) {
      noise(g, w, h, color, 0.05, r(), 2);
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++) {
        // Rusticated ground-floor lines on the lower storey.
        if (f === 1) {
          g.fillStyle = shade(color, 0.88);
          for (let y = fh + 6; y < h; y += 10) g.fillRect(0, y, w, 1.2);
        }
        g.fillStyle = shade(color, 0.8);
        g.fillRect(0, f * fh + 2, w, 3); // string course / cornice
        for (let b = 0; b < 4; b++) {
          const x = b * bw + bw * 0.27,
            y = f * fh + fh * 0.2,
            ww = bw * 0.46,
            hh = fh * 0.62;
          g.fillStyle = shade(color, 0.86);
          g.fillRect(x - 3, y - 6, ww + 6, 5); // pediment / hood
          g.fillRect(x - 2, y + hh, ww + 4, 3); // sill
          sash(g, x, y, ww, hh, r, '#fbfaf6');
        }
      }
    },
  },
  london_stock: {
    colors: ['#b7a07a', '#a99474', '#c0a77e', '#9e8a6c'],
    draw(g, w, h, r, color) {
      bricks(g, 0, 0, w, h, color, '#cfc6b2', r(), 4, 10);
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++)
        for (let b = 0; b < 4; b++) {
          const x = b * bw + bw * 0.28,
            y = f * fh + fh * 0.22,
            ww = bw * 0.44,
            hh = fh * 0.6;
          g.fillStyle = '#8d4a33';
          g.fillRect(x - 2, y - 6, ww + 4, 6); // gauged-brick arch
          g.fillStyle = '#e8e2d6';
          g.fillRect(x - 2, y + hh, ww + 4, 3);
          sash(g, x, y, ww, hh, r, '#f4f1ea');
        }
    },
  },
  red_brick: {
    colors: ['#8e4b37', '#9a5640', '#7f4233', '#a3624a'],
    draw(g, w, h, r, color) {
      bricks(g, 0, 0, w, h, color, '#c4b6a4', r(), 4, 10);
      const bw = w / 4,
        fh = h / 2;
      g.fillStyle = '#e4dccd';
      g.fillRect(0, fh - 4, w, 3); // stone band
      for (let f = 0; f < 2; f++)
        for (let b = 0; b < 4; b++) {
          const x = b * bw + bw * 0.25,
            y = f * fh + fh * 0.2,
            ww = bw * 0.5,
            hh = fh * 0.6;
          g.fillStyle = '#ece4d6';
          g.fillRect(x - 3, y - 4, ww + 6, 4);
          g.fillRect(x - 3, y + hh, ww + 6, 4);
          sash(g, x, y, ww, hh, r, '#f2eee6');
        }
    },
  },
  portland_stone: {
    colors: ['#dcd5c4', '#d6cdb9', '#e3dccb'],
    draw(g, w, h, r, color) {
      noise(g, w, h, color, 0.06, r(), 2);
      g.fillStyle = shade(color, 0.9);
      for (let y = 0; y < h; y += 12) g.fillRect(0, y, w, 1);
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++)
        for (let b = 0; b < 4; b++) {
          const x = b * bw + bw * 0.24,
            y = f * fh + fh * 0.18,
            ww = bw * 0.52,
            hh = fh * 0.64;
          g.fillStyle = shade(color, 0.82);
          g.fillRect(x - 3, y - 3, ww + 6, hh + 7);
          glass(g, x, y, ww, hh, r, '#33414c');
          g.fillStyle = shade(color, 0.7);
          g.fillRect(x + ww / 2 - 1, y, 2, hh);
        }
    },
  },
  glass: {
    colors: ['#5d7486', '#4f6577', '#6a8092', '#567067'],
    draw(g, w, h, r, color) {
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++)
        for (let b = 0; b < 4; b++) glass(g, b * bw, f * fh, bw, fh, r, color);
      g.fillStyle = '#c9cfd3';
      for (let b = 0; b <= 8; b++) g.fillRect((b * w) / 8 - 1, 0, 2, h);
      for (let f = 0; f <= 2; f++) g.fillRect(0, f * fh - 3, w, 6);
      g.fillStyle = 'rgba(40,48,56,0.55)';
      for (let f = 0; f < 2; f++) g.fillRect(0, f * fh + fh - 10, w, 7); // spandrel
    },
  },
  modern_clad: {
    colors: ['#c9c4bb', '#a7a39d', '#d8d2c5', '#8f8b86', '#b9a58b'],
    draw(g, w, h, r, color) {
      noise(g, w, h, color, 0.04, r(), 4);
      const fh = h / 2;
      g.strokeStyle = shade(color, 0.85);
      g.lineWidth = 1;
      for (let x = 0; x < w; x += w / 8) {
        g.beginPath();
        g.moveTo(x, 0);
        g.lineTo(x, h);
        g.stroke();
      }
      for (let f = 0; f < 2; f++) {
        const y = f * fh + fh * 0.28;
        for (let b = 0; b < 4; b++) {
          const x = (b * w) / 4 + 4;
          glass(g, x, y, w / 4 - 8, fh * 0.5, r, '#34424e');
        }
        g.fillStyle = shade(color, 0.75);
        g.fillRect(0, y + fh * 0.5, w, 2);
      }
    },
  },
  concrete: {
    colors: ['#b1ada5', '#a39f97', '#bdb8ae'],
    draw(g, w, h, r, color) {
      noise(g, w, h, color, 0.1, r(), 2);
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++) {
        g.fillStyle = shade(color, 0.86);
        g.fillRect(0, f * fh + fh - 8, w, 8); // balcony slab edge
        for (let b = 0; b < 4; b++)
          glass(g, b * bw + bw * 0.12, f * fh + fh * 0.18, bw * 0.76, fh * 0.56, r, '#3a4652');
      }
    },
  },
  metal_clad: {
    colors: ['#8d969c', '#a2a8a6', '#6f7f86', '#b9b3a5'],
    draw(g, w, h, r, color) {
      g.fillStyle = color;
      g.fillRect(0, 0, w, h);
      for (let x = 0; x < w; x += 6) {
        g.fillStyle = shade(color, x % 12 ? 0.9 : 1.08);
        g.fillRect(x, 0, 3, h);
      }
      g.fillStyle = 'rgba(60,70,80,0.7)';
      g.fillRect(0, h * 0.06, w, h * 0.08);
    },
  },
  ragstone: {
    colors: ['#a49c88', '#9b927e', '#b1a891'],
    draw(g, w, h, r, color) {
      const rr = rng(r());
      g.fillStyle = shade(color, 0.7);
      g.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 7)
        for (let x = -rr() * 8; x < w; x += 8 + rr() * 8) {
          g.fillStyle = shade(color, 0.8 + rr() * 0.4);
          g.fillRect(x + 1, y + 1, 6 + rr() * 8, 5);
        }
      const bw = w / 2;
      for (let b = 0; b < 2; b++) {
        const x = b * bw + bw * 0.38,
          ww = bw * 0.24,
          y = h * 0.15,
          hh = h * 0.6;
        g.fillStyle = '#d6cfbd';
        g.beginPath();
        g.moveTo(x - 3, y + hh);
        g.lineTo(x - 3, y + ww / 2);
        g.arc(x + ww / 2, y + ww / 2, ww / 2 + 3, Math.PI, 0);
        g.lineTo(x + ww + 3, y + hh);
        g.fill();
        g.fillStyle = '#3b4650';
        g.beginPath();
        g.moveTo(x, y + hh);
        g.lineTo(x, y + ww / 2);
        g.arc(x + ww / 2, y + ww / 2, ww / 2, Math.PI, 0);
        g.lineTo(x + ww, y + hh);
        g.fill();
      }
    },
  },
  timber: {
    colors: ['#8a6a4a', '#6f5a45'],
    draw(g, w, h, r, color) {
      g.fillStyle = color;
      g.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 5) {
        g.fillStyle = shade(color, 0.85 + (y % 10) * 0.02);
        g.fillRect(0, y, w, 1);
      }
      const bw = w / 4,
        fh = h / 2;
      for (let f = 0; f < 2; f++)
        for (let b = 0; b < 4; b++)
          glass(g, b * bw + bw * 0.25, f * fh + fh * 0.22, bw * 0.5, fh * 0.55, r);
    },
  },
};

export function facadeTexture(style, variant = 0) {
  const def = FACADES[style] ?? FACADES.london_stock;
  const color = def.colors[variant % def.colors.length];
  return canvasTexture(`facade:${style}:${variant}`, 512, 256, (g, w, h) =>
    def.draw(g, w, h, rng(0.137 + variant * 0.31 + style.length * 0.017), color),
  );
}

// Ground-floor shopfronts (one storey high, 4 bays wide).
export function shopTexture(variant = 0) {
  const fascias = ['#1d3b2f', '#7a1f24', '#1f2f4a', '#2b2b2b', '#c7b28b', '#5a2d4f'];
  return canvasTexture(`shop:${variant}`, 512, 128, (g, w, h) => {
    const r = rng(0.71 + variant * 0.13);
    g.fillStyle = '#d8d0c0';
    g.fillRect(0, 0, w, h);
    for (let b = 0; b < 4; b++) {
      const x = (b * w) / 4;
      g.fillStyle = fascias[(variant + b * 3) % fascias.length];
      g.fillRect(x + 3, 6, w / 4 - 6, 22);
      g.fillStyle = 'rgba(255,255,255,0.7)';
      g.fillRect(x + 20, 14, w / 4 - 40, 5);
      glass(g, x + 8, 34, w / 4 - 16, h - 40, r, '#2d3a44');
      g.fillStyle = 'rgba(250,236,200,0.35)';
      g.fillRect(x + 8, 60, w / 4 - 16, h - 66);
    }
  });
}

export const ROOFS = {
  slate: ['#4f555c', '#5a5f66', '#474c52'],
  clay: ['#8f4a35', '#9c5a40', '#7d4030'],
  flat: ['#8b8a86', '#7c7b78', '#96938c'],
  green: ['#6d7f4f'],
  lead: ['#7d8589'],
};

export function roofTexture(kind, variant = 0) {
  const list = ROOFS[kind] ?? ROOFS.flat;
  const color = list[variant % list.length];
  return canvasTexture(`roof:${kind}:${variant}`, 256, 256, (g, w, h) => {
    const r = rng(0.3 + variant * 0.2 + kind.length * 0.01);
    if (kind === 'slate' || kind === 'clay' || kind === 'lead') {
      g.fillStyle = shade(color, 0.75);
      g.fillRect(0, 0, w, h);
      const row = kind === 'clay' ? 10 : 8;
      for (let y = 0, k = 0; y < h; y += row, k++)
        for (let x = k % 2 ? -8 : 0; x < w; x += 16) {
          g.fillStyle = shade(color, 0.85 + r() * 0.3);
          g.fillRect(x + 0.5, y + 0.5, 15, row - 1.5);
        }
    } else {
      noise(g, w, h, color, 0.18, r(), 2);
      g.fillStyle = shade(color, 0.8);
      for (let i = 0; i < 6; i++) g.fillRect(r() * w, r() * h, 10 + r() * 30, 2);
    }
  });
}

export const GROUND = {
  base: '#7b8466',
  grass: '#6f9152',
  park: '#6a8f4c',
  wood: '#4c6b3a',
  scrub: '#6d7d4a',
  pitch: '#5f9a48',
  playground: '#b49c78',
  track: '#a5523d',
  plaza: '#b9b2a4',
  parking: '#6b6b6b',
  railway: '#7b7266',
  bare: '#9b8a6e',
  cemetery: '#6f8a57',
  allotments: '#7d8a4a',
  sand: '#d8c89a',
  wetland: '#5f7a5a',
  water: '#4f7287',
};

export function groundTexture(kind) {
  const color = GROUND[kind] ?? GROUND.base;
  return canvasTexture(`ground:${kind}`, 256, 256, (g, w, h) => {
    const r = rng(0.5 + kind.length * 0.031);
    noise(g, w, h, color, kind === 'water' ? 0.08 : 0.22, r(), 4);
    if (kind === 'pitch') {
      for (let x = 0; x < w; x += 32) {
        g.fillStyle = 'rgba(255,255,255,0.06)';
        g.fillRect(x, 0, 16, h);
      }
    } else if (kind === 'plaza') {
      g.fillStyle = 'rgba(0,0,0,0.12)';
      for (let x = 0; x < w; x += 16) g.fillRect(x, 0, 1, h);
      for (let y = 0; y < h; y += 16) g.fillRect(0, y, w, 1);
    } else if (kind === 'parking') {
      g.fillStyle = 'rgba(255,255,255,0.5)';
      for (let x = 0; x < w; x += 26) g.fillRect(x, 0, 2, h * 0.4);
    } else if (kind === 'base') {
      for (let i = 0; i < 90; i++) {
        g.fillStyle = r() < 0.5 ? 'rgba(80,110,60,0.35)' : 'rgba(150,140,120,0.25)';
        g.beginPath();
        g.arc(r() * w, r() * h, 4 + r() * 14, 0, Math.PI * 2);
        g.fill();
      }
    }
  });
}

// Road surfaces: u across the carriageway (0..1), v along it (1 unit = 16 m).
export function roadTexture(kind) {
  return canvasTexture(`road:${kind}`, 128, 256, (g, w, h) => {
    const r = rng(0.9 + kind.length * 0.01);
    const base = {
      major: '#46484b',
      minor: '#505255',
      service: '#5a5b5c',
      footway: '#a9a397',
      path: '#b7a98a',
      cycleway: '#7a4a44',
      pavement: '#9d988e',
      rail: '#6a6157',
      steps: '#bdb6a8',
    }[kind];
    noise(g, w, h, base, 0.12, r(), 2);
    if (kind === 'major' || kind === 'minor') {
      g.fillStyle = '#e8e4d8';
      g.fillRect(4, 0, 3, h);
      g.fillRect(w - 7, 0, 3, h);
      if (kind === 'major') {
        g.fillStyle = '#e9e2b0';
        for (let y = 0; y < h; y += 64) g.fillRect(w / 2 - 2, y, 4, 36);
      } else {
        g.fillStyle = '#e8e4d8';
        for (let y = 0; y < h; y += 64) g.fillRect(w / 2 - 1.5, y, 3, 24);
      }
    } else if (kind === 'pavement') {
      g.fillStyle = 'rgba(0,0,0,0.13)';
      for (let y = 0; y < h; y += 14) g.fillRect(0, y, w, 1);
      for (let x = 0; x < w; x += 20) g.fillRect(x, 0, 1, h);
      g.fillStyle = '#c9c4b8';
      g.fillRect(0, 0, 8, h);
      g.fillRect(w - 8, 0, 8, h);
    } else if (kind === 'rail') {
      g.fillStyle = '#4a3b2c';
      for (let y = 0; y < h; y += 10) g.fillRect(w * 0.18, y, w * 0.64, 4);
      g.fillStyle = '#b8bcc0';
      g.fillRect(w * 0.3, 0, 3, h);
      g.fillRect(w * 0.68, 0, 3, h);
    } else if (kind === 'steps') {
      g.fillStyle = 'rgba(0,0,0,0.25)';
      for (let y = 0; y < h; y += 12) g.fillRect(0, y, w, 2);
    }
  });
}
