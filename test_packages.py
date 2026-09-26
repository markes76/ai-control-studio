"""Tests use temporary configurations and never execute downloaded packages."""
import unittest,tempfile,json,zipfile,sys
from pathlib import Path
import catalog as c,packages as p

class Bundles(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.originals=(c.ROOT,c.CACHE,c.MANIFEST,c.CODE,c.routing.DESKTOP_SETTINGS)
  c.ROOT=self.root/'state';c.CACHE=c.ROOT/'catalog.json';c.MANIFEST=c.ROOT/'installs.json';c.CODE=self.root/'code.json';c.routing.DESKTOP_SETTINGS=self.root/'desktop.json'
  c.save(c.CODE,{'keep':True,'mcpServers':{'existing':{'command':'keep'}}});c.save(c.routing.DESKTOP_SETTINGS,{'deploymentMode':'3p','mcpServers':{'existing':{'command':'keep'}}})
  self.e=next(e for e in c.catalog()['entries'] if e['slug']=='word-by-anthropic');self.ident=self.e['_id']
 def tearDown(self):
  c.ROOT,c.CACHE,c.MANIFEST,c.CODE,c.routing.DESKTOP_SETTINGS=self.originals;self.temp.cleanup()
 def bundle(self,path,extra=None):
  m={'manifest_version':'0.3','name':'test-server','version':'1.0.0','server':{'type':'python','entry_point':'server.py','mcp_config':{'command':'python3','args':['${__dirname}/server.py','${user_config.folder}']}},'user_config':{'folder':{'type':'directory','required':True}},'compatibility':{'platforms':['darwin']}}
  with zipfile.ZipFile(path,'w') as z:
   z.writestr('manifest.json',json.dumps(m));z.writestr('server.py','print("fixture")')
   if extra:z.writestr(extra,'unsafe')
 def test_download_does_not_install_then_dual_lifecycle(self):
  src=self.root/'fixture.mcpb';self.bundle(src);before=c.CODE.read_bytes();v=p.get(self.ident,import_path=str(src));self.assertEqual(before,c.CODE.read_bytes())
  with self.assertRaises(ValueError):p.install(self.ident,'wrong',['code'],{'folder':'/tmp'})
  p.install(self.ident,v['sha256'],['desktop','code'],{'folder':'/tmp'})
  for target,path in [('desktop',c.routing.DESKTOP_SETTINGS),('code',c.CODE)]:
   data=c.read(path,{});self.assertIn('existing',data['mcpServers']);self.assertIn(c.name(self.e),data['mcpServers'])
  p.install(self.ident,v['sha256'],['desktop','code'],{'folder':'/tmp'})
  p.uninstall(self.ident,['desktop','code']);self.assertEqual(list(c.read(c.CODE,{})['mcpServers']),['existing'])
  self.assertTrue(Path(v['path']).exists())
 def test_unsafe_archive_and_changed_download_rejected(self):
  src=self.root/'bad.mcpb';self.bundle(src,'../escape')
  with self.assertRaises(ValueError):p.get(self.ident,import_path=str(src))
  self.bundle(src);v=p.get(self.ident,import_path=str(src));Path(v['path']).write_bytes(b'changed')
  with self.assertRaises(ValueError):p.inspect(self.ident)
 def test_conflict_preserves_both_clients(self):
  src=self.root/'fixture.mcpb';self.bundle(src);v=p.get(self.ident,import_path=str(src))
  data=c.read(c.CODE,{});data['mcpServers'][c.name(self.e)]={'command':'another'};c.save(c.CODE,data)
  before=c.routing.DESKTOP_SETTINGS.read_bytes()
  with self.assertRaises(ValueError):p.install(self.ident,v['sha256'],['desktop','code'],{'folder':'/tmp'})
  self.assertEqual(before,c.routing.DESKTOP_SETTINGS.read_bytes())
 def test_write_failure_rolls_back(self):
  before=c.CODE.read_bytes();real=c.save
  def fail(path,data):
   if path==c.routing.DESKTOP_SETTINGS:raise OSError('simulated failure')
   real(path,data)
  c.save=fail
  try:
   with self.assertRaises(OSError):p.transaction({c.CODE:{'changed':True},c.routing.DESKTOP_SETTINGS:{}})
   self.assertEqual(before,c.CODE.read_bytes())
  finally:c.save=real

if __name__=='__main__':unittest.main()
