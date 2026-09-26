"""Audit public publisher sources for every local directory entry; never run their code."""
import json,re,urllib.request,urllib.error,concurrent.futures,datetime
from pathlib import Path
BASE=Path(__file__).parent

def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Gateway-MCP-Catalog/1.0'})
 with urllib.request.urlopen(req,timeout=15) as r:return r.read(4_000_000).decode('utf-8','replace'),r.url

def audit(e):
 result={'id':e['_id'],'title':e['title'],'slug':e['slug'],'directoryUrl':e['directoryUrl'],'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':[],'packages':[],'configurations':[],'errors':[]}
 ident=e['_id'].removeprefix('connector.');repo=None
 if ident.startswith('ant.dir.gh.'):
  parts=ident.removeprefix('ant.dir.gh.').split('.',1)
  if len(parts)==2:repo='/'.join(parts)
 author=e.get('authorUrl') or ''
 match=re.match(r'https://github.com/([^/]+/[^/#?]+)',author)
 if match:repo=match[1]
 if not repo:
  result['status']='registry-or-publisher-setup';result['note']='No public repository linked. Claude registry may require Claude account sign-in.';return result
 result['repository']='https://github.com/'+repo
 # The directory ID is a repository hint, not proof. Only accept public responses.
 for branch in ('main','master'):
  url=f'https://raw.githubusercontent.com/{repo}/{branch}/README.md'
  try:
   text,_=get(url);result['sources'].append(url)
   for m in re.finditer(r'```(?:json|jsonc)?\s*\n(.*?)```',text,re.S):
    block=m[1]
    if 'mcpServers' in block or 'mcp_config' in block:result['configurations'].append(block[:12000])
   for url2 in re.findall(r'https://[^\s<>"\)]+\.(?:mcpb|dxt)(?:\?[^\s<>"\)]*)?',text):
    if 'YOUR' not in url2 and '{' not in url2:result['packages'].append({'url':url2,'evidence':url,'name':url2.rsplit('/',1)[-1]})
   break
  except Exception as err:result['errors'].append(f'README {branch}: {str(err)[:120]}')
 try:
  page,final=get('https://github.com/'+repo+'/releases/latest');result['sources'].append(final)
  tag=final.split('/releases/tag/',1)[1] if '/releases/tag/' in final else None
  if tag:
   assets,asseturl=get('https://github.com/'+repo+'/releases/expanded_assets/'+tag)
   for path in re.findall(r'href="([^"]+\.(?:mcpb|dxt))"',assets):
    url='https://github.com'+path if path.startswith('/') else path
    result['packages'].append({'url':url,'evidence':asseturl,'name':url.rsplit('/',1)[-1]})
 except Exception as err:result['errors'].append('Release: '+str(err)[:160])
 result['packages']=list({p['url']:p for p in result['packages']}.values())
 result['status']='package-found' if result['packages'] else 'configuration-found' if result['configurations'] else 'publisher-setup'
 return result

if __name__=='__main__':
 entries=[e for e in json.loads((BASE/'catalog-seed.json').read_text())['entries'] if e['type']=='local']
 results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  for r in pool.map(audit,entries):results.append(r)
 data={'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'entries':results}
 (BASE/'local-sources.json').write_text(json.dumps(data,indent=2))
 from collections import Counter
 print(json.dumps(dict(Counter(r['status'] for r in results))))
