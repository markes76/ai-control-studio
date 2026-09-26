import unittest,json
from pathlib import Path
import catalog

class ProviderGuidesTest(unittest.TestCase):
 def test_guides_match_only_reviewed_endpoints(self):
  guides=json.loads(Path('provider-guides.json').read_text())['guides']
  self.assertEqual(len(guides),12)
  entries=catalog.catalog()['entries']
  for guide in guides:
   entry=next(e for e in entries if e['slug']==guide['slug'])
   self.assertEqual(entry['serverUrl'],guide['endpoint'])
   self.assertEqual(entry['setupGuide'],guide)
   for step in guide['steps']:
    self.assertTrue(step['url'].startswith('https://'))
    self.assertTrue(step['description'])
 def test_static_oauth_is_not_presented_as_url_only(self):
  guides={g['slug']:g for g in json.loads(Path('provider-guides.json').read_text())['guides']}
  self.assertTrue(guides['asana']['requiresCredentials'])
  self.assertTrue(guides['slack']['requiresCredentials'])
  self.assertFalse(guides['linear']['requiresCredentials'])
 def test_unknown_publishers_do_not_inherit_brand_guides(self):
  for entry in catalog.catalog()['entries']:
   if 'setupGuide' in entry:
    self.assertEqual(entry['serverUrl'],entry['setupGuide']['endpoint'])
    self.assertEqual(entry['slug'],entry['setupGuide']['slug'])

if __name__=='__main__':unittest.main()
