"""Owner-controlled source ZIP -> signed APK -> complete GitHub release.
One ZIP publishes Android and the iPhone PWA. No PR execution or secrets in assets.
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

def public_version(config):
    match=re.search(r'ciVersionName"\).*?getOrElse\("([^"]+)"',config)
    if not match or not re.fullmatch(r'[1-9][0-9]*',match.group(1)):
        raise ValueError('A versão pública deve ser um inteiro: 16, 17, 18...')
    return match.group(1)

def prepare_web(project, version, destination):
    ios=project/'ios'; web=ios/'dist'
    if not (ios/'package-lock.json').is_file(): raise ValueError('ZIP sem versão iPhone ou lockfile de testes')
    if json.loads((web/'version.json').read_text()).get('version')!=version: raise ValueError('Versão iPhone diferente do Android')
    if f"APP_VERSION = '{version}'" not in (web/'version.js').read_text() or f"APP_VERSION = '{version}'" not in (web/'sw.js').read_text(): raise ValueError('Cache iPhone com versão incorreta')
    for name in ['index.html','manifest.webmanifest','app.js','storage.js','core.js','updates.js','style.css','assets/apple-touch-icon.png']:
        if not (web/name).is_file(): raise ValueError('Arquivo iPhone ausente: '+name)
    run(['npm','ci','--ignore-scripts','--no-audit','--no-fund'],cwd=ios)
    run(['npm','test'],cwd=ios)
    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(web,destination)

def already_published(repo, version, commit):
    result=subprocess.run(['gh','release','view','v'+version,'--repo',repo,'--json','isDraft,targetCommitish'],capture_output=True,text=True)
    if result.returncode:
        if 'release not found' in result.stderr.lower() or 'not found' in result.stderr.lower(): return False
        raise ValueError('Não foi possível verificar a versão já publicada: '+result.stderr)
    release=json.loads(result.stdout)
    if not release['isDraft'] and commit and release['targetCommitish']==commit:
        return True
    raise ValueError('Essa versão já existe. Use o próximo número inteiro antes de publicar novamente.')

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
        version=public_version(config)
        prepare_web(project,version,ROOT/'web-dist')
        if already_published(repo,version,os.environ.get('GITHUB_SHA','')):
            print('Android já publicado neste commit; site preparado novamente.');return
        # Key exists only in the runner temporary directory; do not print it.
        key=temp/'signature.jks';key.write_bytes(base64.b64decode(os.environ['BIPADO_SIGNING_KEY_B64'],validate=True));key.chmod(0o600)
        sdk=pathlib.Path(os.environ.get('ANDROID_HOME',os.environ.get('ANDROID_SDK_ROOT','')))
        if not (sdk/'build-tools/34.0.0/apksigner').exists(): raise ValueError('Android SDK ausente')
        (project/'local.properties').write_text('sdk.dir='+str(sdk)+'\n')
        version=public_version(config)
        args=['gradle','--no-daemon','-p',str(project),'-PbipadoSigningKey='+str(key),'-PciVersionCode='+str(code),'-PciVersionName='+version,'-PupdateRepository='+repo,'assembleDebug','lintDebug']
        run(args)
        # Compile/run pure Kotlin regression cases with the compiler already resolved by Gradle.
        cache=pathlib.Path.home()/'.gradle/caches/modules-2/files-2.1'
        pats=['org.jetbrains.kotlin/kotlin-compiler-embeddable/2.0.21','org.jetbrains.kotlin/kotlin-stdlib/2.0.21','org.jetbrains.kotlin/kotlin-script-runtime','org.jetbrains.kotlin/kotlin-reflect','org.jetbrains.intellij.deps/trove4j','org.jetbrains.kotlinx/kotlinx-coroutines-core-jvm','org.jetbrains/annotations']
        jars=[str(p) for pattern in pats for p in (cache/pattern).rglob('*.jar')]
        stdlib=next((cache/'org.jetbrains.kotlin/kotlin-stdlib/2.0.21').rglob('*.jar'));tests=temp/'tests.jar'
        sources=[src/(n+'.kt') for n in ['AddressExtractor','OcrLayout','AddressIdentity','AddressText','GeoAddress','UpdatePolicy','CaptureAddressValidation','ManualAddressValidation','DuplicatePackageLabel','FrameAcquisition']]+[project/n for n in ['geo_regression.kt','address_parser_test.kt','regression.kt','duplicate_regression.kt','screenshot_replay.kt','update_regression.kt','screen_layout_regression.kt','manual_address_regression.kt','capture_safety_regression.kt','frame_acquisition_regression.kt','orphan_icon_regression.kt']]
        run(['java','-cp',os.pathsep.join(jars),'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-classpath',str(stdlib),'-d',str(tests),*map(str,sources)])
        for test in ['Geo_regressionKt','Address_parser_testKt','RegressionKt','Duplicate_regressionKt','Screenshot_replayKt','Update_regressionKt','Screen_layout_regressionKt','Manual_address_regressionKt','Capture_safety_regressionKt','br.com.leitorencomendas.Frame_acquisition_regressionKt','Orphan_icon_regressionKt']:run(['java','-cp',str(tests)+os.pathsep+str(stdlib),test],cwd=project)
        # Test real Store + CSV code against an in-memory Android preference boundary.
        jsonjar=temp/'json-20240303.jar'
        with urllib.request.urlopen('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',timeout=30) as response:
            jsonjar.write_bytes(response.read())
        if hashlib.sha256(jsonjar.read_bytes()).hexdigest()!='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed':
            raise ValueError('Dependência de testes inválida')
        storetests=temp/'store-tests.jar'
        storesrc=[src/(n+'.kt') for n in ['Store','AddressIdentity','AddressText','DuplicatePackageLabel','RouteCsv','WhatsappPolicy']]
        storesrc += [project/'verification/store'/n for n in ['Context.kt','StoreSequenceRegression.kt','SameAddressRegression.kt','RouteCsvRegression.kt','GroupedCardsRegression.kt','AndroidCsvFixture.kt','WhatsappRegression.kt']]
        testcp=str(stdlib)+os.pathsep+str(jsonjar)
        run(['java','-cp',os.pathsep.join(jars),'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-classpath',testcp,'-d',str(storetests),*map(str,storesrc)])
        for test in ['SameAddressRegressionKt','StoreSequenceRegressionKt','RouteCsvRegressionKt','GroupedCardsRegressionKt','WhatsappRegressionKt']:
            run(['java','-cp',str(storetests)+os.pathsep+testcp,test],cwd=project)
        # The Intent boundary double is outside app/src; execute the real dispatch helper.
        if (src/'SpokeShare.kt').is_file():
            spoketests=temp/'spoke-tests.jar'
            spokesrc=[src/'SpokeShare.kt', project/'verification/spoke/Intent.kt', project/'verification/spoke/SpokeShareRegression.kt']
            run(['java','-cp',os.pathsep.join(jars),'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-classpath',str(stdlib),'-d',str(spoketests),*map(str,spokesrc)])
            run(['java','-cp',str(spoketests)+os.pathsep+str(stdlib),'SpokeShareRegressionKt'],cwd=project)
        csv_fixture=temp/'android-export.csv';phone_fixture=temp/'android-whatsapp-export.csv';spoke_fixture=temp/'android-spoke-export.csv'
        run(['java','-cp',str(storetests)+os.pathsep+testcp,'AndroidCsvFixtureKt',str(csv_fixture),str(phone_fixture),str(spoke_fixture)],cwd=project)
        if csv_fixture.read_bytes()!=(project/'ios/tests/fixtures/android-export.csv').read_bytes(): raise ValueError('CSV Android diferente da referência testada no iPhone')
        if phone_fixture.read_bytes()!=(project/'ios/tests/fixtures/android-whatsapp-export.csv').read_bytes(): raise ValueError('CSV WhatsApp Android diferente do iPhone')
        if spoke_fixture.read_bytes()!=(project/'ios/tests/fixtures/android-spoke-export.csv').read_bytes(): raise ValueError('CSV para Spoke diferente entre Android e iPhone')
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
        run(['gh','release','create',tag,str(dest),str(m),'--repo',repo,'--draft','--target',os.environ.get('GITHUB_SHA','main'),'--title',f'BIPADO DE ROTA VERSÃO {version}','--notes','VERSÃO '+version+': corrige exportação para o Spoke: envia somente endereços e números dos pacotes, sem contatos WhatsApp. BAIXAR ROTAS mantém contatos para transferir entre Android e iPhone. Design, pacotes, ordem e demais funções preservados. Testes automatizados e assinatura verificados; valide o novo CSV no Spoke no celular. Atualize sem desinstalar.'])
        run(['gh','release','edit',tag,'--repo',repo,'--draft=false','--latest'])
        print('Release publicada:',tag)

if __name__=='__main__':main()




