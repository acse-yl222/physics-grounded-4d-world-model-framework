import {surface} from './mesh.mjs';
let data;
self.onmessage=({data:message})=>{
  if(message.data)data=message.data;
  try{
    const result=surface({...data,...message.options});
    self.postMessage({id:message.id,...result},[result.position.buffer,result.uv.buffer,result.kind.buffer,result.light.buffer,result.index.buffer]);
  }catch(error){self.postMessage({id:message.id,error:String(error)});}
};
