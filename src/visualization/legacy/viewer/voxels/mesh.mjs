// Extract exposed faces directly from little-endian packed solid[z,y,x].
// Two passes bound memory, and indexed quads retain each individual cell face.
export function surface({bits,study,terrain,nx,ny,nz,cell,ox,oy,xcut,zcut,padding}) {
  const plane=nx*ny, bit=(a,i)=>(a[i>>3]>>(i&7))&1;
  const inside=(x,y,z)=>x>=0&&x<xcut&&y>=0&&y<ny&&z>=0&&z<zcut&&
    (padding||bit(study,y*nx+x))&&bit(bits,z*plane+y*nx+x);
  const directions=[[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]];
  const corners=[[[1,0,0],[1,1,0],[1,1,1],[1,0,1]],[[0,1,0],[0,0,0],[0,0,1],[0,1,1]],
    [[1,1,0],[0,1,0],[0,1,1],[1,1,1]],[[0,0,0],[1,0,0],[1,0,1],[0,0,1]],
    [[0,0,1],[1,0,1],[1,1,1],[0,1,1]],[[0,1,0],[1,1,0],[1,0,0],[0,0,0]]];
  const shade=[.74,.58,.68,.86,1,.42];
  let faces=0, occupied=0;
  function walk(visit){for(let z=0;z<Math.min(nz,zcut);z++)for(let y=0;y<ny;y++)for(let x=0;x<Math.min(nx,xcut);x++){
    if(!inside(x,y,z))continue;
    if(!visit)occupied++;
    for(let d=0;d<6;d++){const [dx,dy,dz]=directions[d];if(!inside(x+dx,y+dy,z+dz)){if(visit)visit(x,y,z,d);else faces++;}}
  }}
  walk(null);
  const position=new Float32Array(faces*12),uv=new Float32Array(faces*8),kind=new Float32Array(faces*4),light=new Float32Array(faces*4),index=new Uint32Array(faces*6);
  let f=0;
  walk((x,y,z,d)=>{
    const structure=z*cell>terrain[y*nx+x];
    for(let k=0;k<4;k++){
      const [a,b,c]=corners[d][k],i=f*4+k;
      position.set([ox+(x+a)*cell,(z+c)*cell,-oy-(y+b)*cell],i*3);
      uv.set([[0,0],[1,0],[1,1],[0,1]][k],i*2);kind[i]=structure?1:0;light[i]=shade[d];
    }
    const i=f*4;index.set([i,i+1,i+2,i,i+2,i+3],f*6);f++;
  });
  return {position,uv,kind,light,index,faces,occupied};
}
