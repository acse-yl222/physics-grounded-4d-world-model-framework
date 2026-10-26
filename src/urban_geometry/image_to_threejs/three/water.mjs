// Animated water for live viewers: ripples as a per-fragment normal perturbation
// on the shared `ground:water` material, plus a slow drift of its texture. Exported
// GLBs keep the static material; viewers opt in with animateWater().
import { ground } from './kit.mjs';

const uniforms = { uWaterTime: { value: 0 } };
let patched = false;

/**
 * Patch the water material once and return a tick(seconds) function that advances
 * the ripples. Viewers place the ENU (z-up) model in a y-up three.js world, so
 * world (x, y, z) is ENU (x, z, -y).
 */
export function animateWater() {
  const material = ground('water');
  if (!patched) {
    patched = true;
    material.onBeforeCompile = (shader) => {
      shader.uniforms.uWaterTime = uniforms.uWaterTime;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWaterWorld;')
        .replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\nvWaterWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;',
        );
      shader.fragmentShader = shader.fragmentShader
        .replace(
          '#include <common>',
          `#include <common>
varying vec3 vWaterWorld;
uniform float uWaterTime;
// Height gradient of a few travelling waves (wavelengths 3-23 m).
vec2 waterSlope(vec2 p, float t) {
  vec2 g = vec2(0.0);
  const vec3 W[5] = vec3[5](
    vec3(0.27, 0.0, 1.3), vec3(0.55, 1.9, 1.7), vec3(0.93, 3.6, 2.4),
    vec3(1.61, 0.8, 3.1), vec3(2.17, 2.7, 3.9));
  for (int i = 0; i < 5; i++) {
    vec2 d = vec2(cos(W[i].y), sin(W[i].y));
    float k = W[i].x;
    float a = 0.035 / (1.0 + float(i));
    g += d * k * a * cos(dot(d, p) * k + t * W[i].z);
  }
  return g;
}`,
        )
        .replace(
          '#include <normal_fragment_maps>',
          `#include <normal_fragment_maps>
{
  vec2 wp = vec2(vWaterWorld.x, -vWaterWorld.z);
  vec2 g = waterSlope(wp, uWaterTime);
  vec3 nWorld = normalize(vec3(-g.x, -g.y, 1.0));
  normal = normalize((viewMatrix * vec4(nWorld.x, nWorld.z, -nWorld.y, 0.0)).xyz);
}`,
        );
    };
    material.customProgramCacheKey = () => 'water-anim';
    material.needsUpdate = true;
  }
  return (seconds) => {
    uniforms.uWaterTime.value = seconds;
    if (material.map) {
      material.map.offset.set(seconds * 0.004, seconds * 0.0025);
    }
  };
}
