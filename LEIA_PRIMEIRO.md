# BIPADO DE ROTA — atualização obrigatória e compilação por ZIP

Repositório: bim536203-bot/bipado-de-rota. A configuração é realizada uma única vez. O APK V5.13 só deve ser distribuído depois da primeira release publicada: ele bloqueia quando não consegue verificar a versão.

## Configuração inicial (uma única vez)
1. Criar repositório público `bim536203-bot/bipado-de-rota`, branch `main`.
2. Enviar os arquivos deste pacote preservando os caminhos `.github/workflows/compilar.yml`, `publicar.py` e `projeto.zip`. Extrair este pacote antes de enviar os arquivos; enviar o ZIP de configuração inteiro não instala o workflow. Ativar GitHub Actions se solicitado.
3. Em Settings > Secrets and variables > Actions, criar `GEOAPIFY_API_KEY` e `BIPADO_SIGNING_KEY_B64` (Base64 do JKS original). Não enviar o JKS, a chave Geoapify ou seu Base64 para os arquivos públicos do repositório. A assinatura original foi preservada; o publicador compara o certificado com o APK V5.12.
4. Rodar Actions > Compilar e publicar BIPADO DE ROTA > Run workflow para a primeira release. As seguintes rodam ao substituir `projeto.zip`.
5. Depois da primeira execução bem-sucedida, instalar o APK publicado sobre a V5.12, sem desinstalar. Isso ativa a atualização dentro do app.

## A cada atualização
Atualizar o código a partir do projeto V5.13 ou posterior, comprimir o projeto completo e enviar substituindo `projeto.zip`. O nome desse arquivo deve permanecer igual. O código das quatro classes de atualização e as configurações Gradle precisam permanecer no projeto. O workflow rejeita um ZIP que remova esses componentes.
A compilação aumenta automaticamente o versionCode; o nome público é um inteiro (16, 17, 18...), sem código incremental no rodapé. O versionCode Android continua crescente separadamente. Após compilar, executar regressões, lint, verificar assinatura e alinhamento, publica APK e update.json juntos. Release em rascunho não aparece nos celulares. Uma compilação que falha não vira versão disponível.

## Comportamento do app
Ao abrir, consulta a versão pela internet. Se há atualização, mostra tela obrigatória e ATUALIZAR, sem botão para ignorar. Se não consegue verificar, mantém bloqueado e mostra TENTAR NOVAMENTE. A indicação de atualização já detectada persiste entre reaberturas e não é anulada por resposta de versão mais antiga. Verificação de rede também ocorre ao iniciar/tocar no leitor e quando a conexão muda. Ao retornar à tela principal após mais de 15 segundos, a versão é consultada novamente.
O download confere tamanho, SHA-256, pacote, número da versão e certificado. O Android ainda exige autorizar esta fonte de instalação e confirmar a instalação. Cancelar ou negar a instalação mantém o bloqueio. Dados são preservados ao instalar sobre a mesma assinatura.

## Validação e limites
Testes de política local e extração segura de ZIP; compilação e lint Android. O fluxo real do GitHub e a instalação pelo atualizador precisam de repositório e segredos ativos e validação no Moto G8 Plus. Sem o endereço publicado, esta versão permanece bloqueada, conforme solicitado.
O processo lê e executa o projeto enviado pelo dono do repositório. Somente quem deve publicar versões pode ter acesso de escrita ao repositório.
GitHub Actions usa runner padrão ubuntu-24.04. Não usa Supabase nem Play Store.


## VERSÃO 17
O pacote projeto.zip contém as correções de captura/layout, edição manual, proteção de leitura ambígua, design de endereço não encontrado, cartões dos pacotes no mesmo endereço e CSV com um destino por endereço e Notes PACOTE 1-2-3. O publicador compila/linta o Android, executa 916 verificações Kotlin, compara a assinatura original e só publica a release após as verificações. Testar o fluxo real em aparelhos e a importação no Spoke após instalar; testes de lógica não substituem uso em dispositivo. O Android ainda pede confirmação de instalação.
