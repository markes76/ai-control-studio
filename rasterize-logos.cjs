const fs=require('fs'),path=require('path');
const sharp=require('sharp');
const folder=path.join(__dirname,'assets/logos');
(async()=>{
 let ok=0,failed=0;const files=fs.readdirSync(folder).filter(x=>x.endsWith('.source'));
 for(let i=0;i<files.length;i+=16) await Promise.all(files.slice(i,i+16).map(async file=>{try{await sharp(path.join(folder,file),{density:144}).resize(96,96,{fit:'contain',background:{r:255,g:255,b:255,alpha:0}}).png().toFile(path.join(folder,file.replace('.source','.png')));ok++}catch(e){failed++}}));
 console.log('Rasterized:',ok,'failed:',failed);
})();
