import test from 'node:test';
import assert from 'node:assert/strict';
import {movieLayout} from '../src/visualization/legacy/viewer/windfarm-movie/layout.mjs';
const legacy = {display_shape:[256,512],display_cell_m:8,display_first_center_offset_m:5,origin_xyz_m:[-1776,-992,0]};
test('legacy sampling coordinates remain aligned with original export',()=>{
 const layout=movieLayout(legacy,256*512);
 assert.deepEqual(layout.position(2,3,140),[-1755,220,963]);
});
test('new spacing, sample offset and height come from recorded metadata',()=>{
 const layout=movieLayout({...legacy,display_cell_m:4,display_first_center_offset_m:2,slice_agl_m:90},256*512);
 assert.deepEqual(layout.position(2,3,140),[-1766,230,978]);
});
test('reject misaligned terrain and absent sampling coordinates',()=>{
 assert.throws(()=>movieLayout(legacy,1));
 assert.throws(()=>movieLayout({...legacy,display_cell_m:undefined},256*512));
});
