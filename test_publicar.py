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
if __name__=='__main__':unittest.main()
