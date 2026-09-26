"""Cache public directory artwork without fetching packages or running MCPs."""
import json,urllib.request,hashlib,concurrent.futures
from pathlib import Path
import catalog
root=Path(__file__).parent/'assets/logos';root.mkdir(parents=True,exist_ok=True)
entries=catalog.catalog()['entries'];urls={e['iconUrl'] for e in entries if e.get('iconUrl')};results={}
def fetch(url):
 name=hashlib.sha256(url.encode()).hexdigest()[:24]
 p=root/(name+'.source')
 try:
  if not p.exists():
   req=urllib.request.Request(url,headers={'User-Agent':'AI-Control-Studio/1.0'})
   with urllib.request.urlopen(req,timeout=15) as r:data=r.read(2_000_001)
   if len(data)>2_000_000:raise ValueError('Oversize artwork')
   p.write_bytes(data)
  return url,name,None
 except Exception as e:return url,None,type(e).__name__
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
 for i,(url,name,error) in enumerate(pool.map(fetch,urls)):
  results[url]={'file':name+'.png' if name else None,'error':error}
  if i%100==0:print(f'Artwork fetched: {i+1}/{len(urls)}',flush=True)
(root/'sources.json').write_text(json.dumps(results,indent=2))
print('Fetched',sum(bool(v['file']) for v in results.values()),'of',len(urls),flush=True)
