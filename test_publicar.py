import pathlib,stat,tempfile,unittest,zipfile
from publicar import extract_source
class SourceZipTests(unittest.TestCase):
 def run_zip(self,entries):
  with tempfile.TemporaryDirectory() as t:
   z=pathlib.Path(t)/'source.zip'
   with zipfile.ZipFile(z,'w') as f:
    for name,text in entries:f.writestr(name,text)
   return extract_source(z,pathlib.Path(t)/'out')
 def test_project(self):self.assertEqual(self.run_zip([('Projeto/settings.gradle.kts',''),('Projeto/app/build.gradle.kts','')]).name,'Projeto')
 def test_traversal(self):
  with self.assertRaises(ValueError):self.run_zip([('../escape','')])
 def test_absolute(self):
  with self.assertRaises(ValueError):self.run_zip([('/escape','')])
 def test_windows(self):
  with self.assertRaises(ValueError):self.run_zip([('..\\escape','')])
 def test_two_projects(self):
  with self.assertRaises(ValueError):self.run_zip([(f'{p}/{f}','') for p in ['one','two'] for f in ['settings.gradle.kts','app/build.gradle.kts']])
 def test_no_project(self):
  with self.assertRaises(ValueError):self.run_zip([('readme.txt','')])
 def test_symlink(self):
  with tempfile.TemporaryDirectory() as t:
   z=pathlib.Path(t)/'link.zip';i=zipfile.ZipInfo('link');i.external_attr=(stat.S_IFLNK|0o777)<<16
   with zipfile.ZipFile(z,'w') as f:f.writestr(i,'/escape')
   with self.assertRaises(ValueError):extract_source(z,pathlib.Path(t)/'out')


class JointPublishTests(unittest.TestCase):
 def test_versions(self):
  from publicar import public_version
  self.assertEqual(public_version('ciVersionName").getOrElse("20")'),'20')
  for value in ['20.1','V20','20-1','0']:
   with self.assertRaises(ValueError):public_version('ciVersionName").getOrElse("'+value+'")')
 def test_web_mismatch(self):
  import json
  from publicar import prepare_web
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'ios/dist').mkdir(parents=True);(p/'ios/package-lock.json').write_text('{}');(p/'ios/dist/version.json').write_text(json.dumps({'version':'19'}))
   with self.assertRaisesRegex(ValueError,'diferente'):prepare_web(p,'20',p/'out')
 def test_rerun_only_same_published_commit(self):
  from unittest.mock import patch
  from subprocess import CompletedProcess
  from publicar import already_published
  with patch('publicar.subprocess.run',return_value=CompletedProcess([],0,'{"isDraft":false,"targetCommitish":"abc"}','')):
   self.assertTrue(already_published('owner/repo','20','abc'))
   with self.assertRaises(ValueError):already_published('owner/repo','20','different')
  with patch('publicar.subprocess.run',return_value=CompletedProcess([],1,'','release not found')):
   self.assertFalse(already_published('owner/repo','20','abc'))

if __name__=='__main__':unittest.main()
