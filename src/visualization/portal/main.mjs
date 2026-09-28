const root=new URL('../../../',import.meta.url),target=document.getElementById('scenes');
try{
 const response=await fetch(new URL('src/visualization/public-scenes.json',root));if(!response.ok)throw Error('无法加载场景目录');const catalog=await response.json();target.replaceChildren();
 for(const item of catalog.scenes){
  const card=document.createElement('article');card.className='card';card.dataset.scene=item.scene_id;
  for(const [tag,content,cls] of [['span',item.tag,'tag'],['h3',item.title,''],['p',item.description,'']]){const node=document.createElement(tag);node.textContent=content;node.className=cls;card.append(node);}
  const link=document.createElement('a');link.className='button';link.textContent='打开场景 →';link.href=new URL(item.viewer_url,root);card.append(link);
  if(item.scene_id!=='windfarm'){
    const quick=document.createElement('a');quick.className='quick-preview';quick.textContent='轻量预览 · 更快加载';
    const url=new URL(link.href);url.searchParams.set('lite','1');quick.href=url;card.append(quick);
  }
  target.append(card);
 }
 for(const id of ['resources','resource-detail'])document.getElementById(id).href=catalog.resources_url;
}catch(error){document.getElementById('error').hidden=false;document.getElementById('error').textContent=error.message;}
