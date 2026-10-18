# BIPADO DE ROTA — VERSÃO 20

## Um único ZIP atualiza Android e iPhone

Nas próximas atualizações, envie o novo projeto completo como **projeto.zip**, substituindo o arquivo na raiz do repositório, e confirme o commit em main. Não extraia o ZIP no GitHub. O ZIP inclui o projeto Android e a pasta ios; mantenha os dois juntos.

O GitHub testa e compila o Android, verifica a assinatura original e publica APK + update.json. Depois publica o aplicativo web do iPhone pelo GitHub Pages. A atualização Android continua sendo oferecida no aplicativo instalado. No iPhone aparece NOVA VERSÃO DISPONÍVEL e o botão ATUALIZAR; a lista importada permanece no aparelho.

Use números inteiros crescentes e iguais nos dois aplicativos: 20, 21, 22… No Android altere ciVersionName em app/build.gradle.kts. Na pasta ios/dist atualize version.js, version.json, sw.js e a etiqueta inicial do index.html. Nunca reutilize um número publicado.

## Usar no iPhone

Abra o link do GitHub Pages no Safari, toque em Compartilhar → Adicionar à Tela de Início. Abra uma vez com internet para preparar o modo offline. No Android use BAIXAR ROTAS, transfira o CSV ao iPhone e toque em IMPORTAR ROTAS CSV.

A versão iPhone consulta, pesquisa, edita, adiciona manualmente, apaga e exporta rotas para o Spoke. Endereços repetidos formam um cartão e uma parada com descrição PACOTE 1-2-3. Listas substituídas ou apagadas ficam no histórico por 24 horas. Não possui captura/OCR nem ícone flutuante. Os dados ficam neste aparelho; não há sincronização automática entre celulares. Guarde o CSV original. Limpar os dados do site/aparelho remove o armazenamento local.

## Configuração inicial (já preparada)

Settings → Pages → Source: GitHub Actions. O workflow compilar.yml publica os dois aplicativos. Preserve os segredos de assinatura e mapas já configurados; nunca os coloque no ZIP. Se apenas a etapa de publicação do site falhar, use Re-run failed jobs. Uma repetição do mesmo commit reconhece o Android já publicado e prepara o site novamente.

## Verificação

Testes Kotlin de regressão + lint Android; testes Node do CSV real exportado pelo Android, agrupamento, histórico, edição, IndexedDB transacional, interface DOM e atualização offline. Os testes automatizados não substituem uma conferência física no Safari/iPhone.
