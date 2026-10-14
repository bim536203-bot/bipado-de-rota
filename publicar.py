"""Owner-controlled source ZIP -> signed APK -> complete GitHub release.
No PR execution, no secrets in source/release assets. Requires the V5.13 updater.
"""
import base64, hashlib, json, os, pathlib, re, shutil, stat, subprocess, tempfile, urllib.error, urllib.request, zipfile
ROOT=pathlib.Path(__file__).resolve().parent
CERT='bd98a11bc48c890c62d9d862d3ab842fa293d435acb58ce2ad985193ecdd43fb'
PACKAGE='br.com.leitorencomendas'

def extract_source(source, destination):
    destination=pathlib.Path(destination).resolve()
    with zipfile.ZipFile(source) as z:
        if sum(i.file_size for i in z.infolist())>100_000_000: raise ValueError('ZIP muito grande')
        for i in z.infolist():
            name=pathlib.PurePosixPath(i.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in i.filename or stat.S_ISLNK(i.external_attr>>16): raise ValueError('Caminho inválido no ZIP')
            if i.flag_bits & 1: raise ValueError('ZIP protegido por senha não é aceito')
            target=destination.joinpath(*name.parts).resolve()
            if not target.is_relative_to(destination): raise ValueError('Caminho fora do projeto')
        z.extractall(destination)
    matches=[p.parent for p in destination.rglob('settings.gradle.kts') if (p.parent/'app/build.gradle.kts').is_file()]
    if len(matches)!=1: raise ValueError('O ZIP precisa conter exatamente um projeto Android')
    return matches[0]

def latest(repo):
    request=urllib.request.Request(f'https://api.github.com/repos/{repo}/releases/latest',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request,timeout=30) as f: release=json.load(f)
    except urllib.error.HTTPError as e:
        if e.code==404: return 64
        raise
    asset=next((a for a in release['assets'] if a['name']=='update.json'),None)
    if asset is None: raise ValueError('Release anterior sem update.json; confira antes de publicar')
    with urllib.request.urlopen(asset['browser_download_url'],timeout=30) as f: manifest=json.load(f)
    if manifest['applicationId']!=PACKAGE or manifest['schema']!=1: raise ValueError('Manifesto incompatível')
    return int(manifest['versionCode'])

def run(args,**kw): return subprocess.run(args,check=True,**kw)

def main():
    repo=os.environ['UPDATE_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo): raise ValueError('Repositório inválido')
    for name in ['GH_TOKEN','GEOAPIFY_API_KEY','BIPADO_SIGNING_KEY_B64']:
        if not os.environ.get(name): raise ValueError('Configure o segredo '+name)
    code=max(65,latest(repo)+1)
    with tempfile.TemporaryDirectory(prefix='bipado-ci-') as work:
        temp=pathlib.Path(work);project=extract_source(ROOT/'projeto.zip',temp/'source')
        src=project/'app/src/main/java/br/com/leitorencomendas'
        for name in ['Updater.kt','UpdateActivity.kt','UpdatePolicy.kt','BipadoApplication.kt']:
            if not (src/name).is_file(): raise ValueError('Este ZIP ainda não contém a atualização obrigatória V5.13: '+name)
        config=(project/'app/build.gradle.kts').read_text()
        for marker in ['ciVersionCode','ciVersionName','updateRepository','bipadoSigningKey']:
            if marker not in config: raise ValueError('Projeto sem configuração automática: '+marker)
        # Key exists only in the runner temporary directory; do not print it.
        key=temp/'signature.jks';key.write_bytes(base64.b64decode(os.environ['BIPADO_SIGNING_KEY_B64'],validate=True));key.chmod(0o600)
        sdk=pathlib.Path(os.environ.get('ANDROID_HOME',os.environ.get('ANDROID_SDK_ROOT','')))
        if not (sdk/'build-tools/34.0.0/apksigner').exists(): raise ValueError('Android SDK ausente')
        (project/'local.properties').write_text('sdk.dir='+str(sdk)+'\n')
        base_version=re.search(r'ciVersionName"\).*?getOrElse\("([^"]+)"',config)
        if not base_version or not re.fullmatch(r'[0-9A-Za-z.+-]{1,50}',base_version.group(1)): raise ValueError('Nome de versão inválido')
        version=f'{base_version.group(1)}-{code}'
        args=['gradle','--no-daemon','-p',str(project),'-PbipadoSigningKey='+str(key),'-PciVersionCode='+str(code),'-PciVersionName='+version,'-PupdateRepository='+repo,'assembleDebug','lintDebug']
        run(args)
        # Compile/run pure Kotlin regression cases with the compiler already resolved by Gradle.
        cache=pathlib.Path.home()/'.gradle/caches/modules-2/files-2.1'
        pats=['org.jetbrains.kotlin/kotlin-compiler-embeddable/2.0.21','org.jetbrains.kotlin/kotlin-stdlib/2.0.21','org.jetbrains.kotlin/kotlin-script-runtime','org.jetbrains.kotlin/kotlin-reflect','org.jetbrains.intellij.deps/trove4j','org.jetbrains.kotlinx/kotlinx-coroutines-core-jvm','org.jetbrains/annotations']
        jars=[str(p) for pattern in pats for p in (cache/pattern).rglob('*.jar')]
        stdlib=next((cache/'org.jetbrains.kotlin/kotlin-stdlib/2.0.21').rglob('*.jar'));tests=temp/'tests.jar'
        sources=[src/(n+'.kt') for n in ['AddressExtractor','OcrLayout','AddressIdentity','AddressText','GeoAddress','UpdatePolicy']]+[project/n for n in ['geo_regression.kt','address_parser_test.kt','regression.kt','duplicate_regression.kt','screenshot_replay.kt','update_regression.kt']]
        run(['java','-cp',os.pathsep.join(jars),'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-classpath',str(stdlib),'-d',str(tests),*map(str,sources)])
        for test in ['Geo_regressionKt','Address_parser_testKt','RegressionKt','Duplicate_regressionKt','Screenshot_replayKt','Update_regressionKt']:run(['java','-cp',str(tests)+os.pathsep+str(stdlib),test],cwd=project)
        apk=project/'app/build/outputs/apk/debug/app-debug.apk';bt=sdk/'build-tools/34.0.0'
        output=subprocess.check_output([str(bt/'apksigner'),'verify','--print-certs',str(apk)],text=True)
        if f'certificate SHA-256 digest: {CERT}' not in output: raise ValueError('Assinatura diferente da versão instalada')
        run([str(bt/'zipalign'),'-c','4',str(apk)])
        badging=subprocess.check_output([str(bt/'aapt'),'dump','badging',str(apk)],text=True)
        if f"name='{PACKAGE}' versionCode='{code}'" not in badging: raise ValueError('Código da versão não foi aplicado')
        tag=f'v{version}';name='BIPADO_DE_ROTA.apk';dest=temp/name;shutil.copy2(apk,dest)
        manifest={'schema':1,'applicationId':PACKAGE,'versionCode':code,'versionName':version,'minSdk':26,'size':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'apkUrl':f'https://github.com/{repo}/releases/download/{tag}/{name}'}
        m=temp/'update.json';m.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        # Draft first: phones cannot see partial or failed builds. Set latest only after all assets exist.
        run(['gh','release','create',tag,str(dest),str(m),'--repo',repo,'--draft','--target',os.environ.get('GITHUB_SHA','main'),'--title',f'BIPADO DE ROTA {version}','--notes','Atualização obrigatória. APK assinado e verificado; dados preservados ao instalar sobre a versão anterior.'])
        run(['gh','release','edit',tag,'--repo',repo,'--draft=false','--latest'])
        print('Release publicada:',tag)

if __name__=='__main__':main()
