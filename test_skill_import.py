import io,json,tempfile,unittest,zipfile,stat
from pathlib import Path
from unittest.mock import patch
import skill_import as si,studio

class SkillImportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def archive(self,files):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   for name,text in files.items():z.writestr('repo-sha/'+name,text)
  return b.getvalue()
 def discovery(self,archive,url='https://github.com/example/skills'):
  with patch.object(si,'public_url',side_effect=lambda x:__import__('urllib.parse').parse.urlsplit(x)),patch.object(si,'fetch',side_effect=[b'{"default_branch":"main"}',b'{"sha":"abcdef"}',archive]):
   return si.discover(url,self.root/'cache')
 def test_discovers_multiple_skills_preserves_support_and_imports(self):
  v=self.discovery(self.archive({'skills/alpha/SKILL.md':'---\nname: alpha\ndescription: Test\n---\nInstructions','skills/alpha/scripts/test.py':'print("not executed")','skills/beta/SKILL.md':'---\nname: beta\n---\nOther'}))
  self.assertEqual(len(v['candidates']),2)
  alpha=v['candidates'][0];self.assertIn('scripts/test.py',alpha['files'])
  result=si.install(self.root/'cache',v['token'],alpha['id'],'alpha-copy',self.root/'installed')
  self.assertIn('name: alpha-copy',Path(result['path']).read_text());self.assertTrue((self.root/'installed/alpha-copy/scripts/test.py').exists())
  with self.assertRaises(ValueError):si.install(self.root/'cache',v['token'],alpha['id'],'alpha-copy',self.root/'installed')
 def test_root_skill_support_and_nested_skill_isolation(self):
  v=self.discovery(self.archive({'SKILL.md':'---\nname: root\n---\nRoot','reference.md':'Reference','nested/SKILL.md':'---\nname: nested\n---\nNested'}))
  root=v['candidates'][0];self.assertIn('reference.md',root['files']);self.assertNotIn('nested/SKILL.md',root['files'])
 def test_folder_url_filters_and_traversal_rejected(self):
  arc=self.archive({'skills/a/SKILL.md':'---\nname: a\n---\nA','skills/b/SKILL.md':'---\nname: b\n---\nB'})
  v=self.discovery(arc,'https://github.com/example/skills/tree/main/skills/a');self.assertEqual(len(v['candidates']),1)
  with self.assertRaises(ValueError):self.discovery(self.archive({'../escape':'x','SKILL.md':'---\n---\n'}))
 def test_preview_cannot_read_other_files_and_reserved_name(self):
  v=self.discovery(self.archive({'skills/a/SKILL.md':'---\nname: a\n---\nA'}))
  with self.assertRaises(ValueError):si.preview_file(self.root/'cache',v['token'],'0','../../secret')
  with self.assertRaises(ValueError):si.install(self.root/'cache',v['token'],'0','synced',self.root/'installed')
 def test_plain_url_and_html_error(self):
  with patch.object(si,'public_url',side_effect=lambda x:__import__('urllib.parse').parse.urlsplit(x)),patch.object(si,'fetch',return_value=b'---\nname: a\n---\nA'):
   v=si.discover('https://example.com/SKILL.md',self.root/'cache');self.assertEqual(v['candidates'][0]['files'],['SKILL.md'])
  with patch.object(si,'public_url',side_effect=lambda x:__import__('urllib.parse').parse.urlsplit(x)),patch.object(si,'fetch',return_value=b'<html>page</html>'):
   with self.assertRaises(ValueError):si.discover('https://example.com',self.root/'cache')
 def test_inventory_symlink_skill_and_sync_readonly(self):
  base=self.root/'.claude';outside=self.root/'outside';outside.mkdir();(outside/'SKILL.md').write_text('---\nname: linked\n---\n')
  (base/'skills').mkdir(parents=True);(base/'skills/linked').symlink_to(outside,target_is_directory=True)
  cache=base/'skills/synced/pdf';cache.mkdir(parents=True);(cache/'SKILL.md').write_text('---\nname: pdf\n---\n')
  with patch.object(studio,'BASE',base),patch.object(studio,'WORK',self.root/'work'):
   rows=studio.inventory()['records'];self.assertTrue(any(x['name']=='linked' for x in rows));self.assertTrue(next(x for x in rows if x['name']=='pdf')['readonly'])
 def test_webpage_offers_skill_sources_without_fetching_them(self):
  html=b'<html><a href="/skills/SKILL.md">Skill</a><a href="https://github.com/example/skills">Repository</a><a href="http://localhost/private">Ignore</a></html>'
  with patch.object(si,'public_url',side_effect=lambda x:__import__('urllib.parse').parse.urlsplit(x)),patch.object(si,'fetch',return_value=html) as fetch:
   v=si.discover('https://example.com/docs',self.root/'cache')
   self.assertEqual(v['sources'],['https://example.com/skills/SKILL.md','https://github.com/example/skills']);self.assertEqual(fetch.call_count,1)
if __name__=='__main__':unittest.main()
