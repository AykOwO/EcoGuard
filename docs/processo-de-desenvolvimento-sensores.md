# Processo de desenvolvimento da parte de sensores (do Chama ao EcoGuard)

Este documento conta como a parte de sensores foi construída, com as tecnologias usadas, os problemas encontrados e o que foi decidido em cada etapa. Ele vai até a primeira versão instalável do **EcoGuard** (versão 1.1.0, de 23/11/2026), com o que foi feito, testado e o que ainda falta.

Os trechos marcados com **[preencher]** são informações que não estão no código nem no histórico do Git e precisam ser completadas pela equipe.

## 1. Ponto de partida: o Chama

O Chama já existia como um web app, feito primeiro para o celular, para **relatar incêndios, organizar quem vai ajudar e acompanhar o risco de fogo** pela regra dos 30 (temperatura acima de 30 °C, umidade do ar abaixo de 30 % e vento acima de 30 km/h). Ele foi feito em Python com Flask. O primeiro envio ao repositório foi em 23/09/2026.

A matéria de extensão **[preencher: nome da disciplina, professora e instituição]** pediu um produto que usasse sensores reais. A equipe decidiu desenvolver a parte de sensores dentro do próprio Chama e, mais tarde, separá-la num app menor.

## 2. Linha do tempo

| Data | O que aconteceu |
| --- | --- |
| 23/09/2026 | Primeiro envio do Chama ao repositório |
| 01/10/2026 | O Chama é reescrito como app completo. Entram o banco de dados com **dispositivos IoT e leituras**, a tela de Sensores, o `simulador_iot.py` e o endpoint `POST /api/leituras`, no qual um aparelho envia medições com código e token |
| 01/10/2026 | O banco passa de `sqlite3` puro para **SQLAlchemy ORM**. Os segredos saem do código e o login vira email e senha, com os dados separados por usuário |
| 01/10/2026 | Entra a **Rede de sensores**: um mapa e uma lista com os sensores de todas as pessoas, com localização aproximada e sem dados do dono |
| 14/10/2026 | O ESP32 do projeto envia suas primeiras leituras à **API dos sensores**, feita em FastAPI (isso aparece nos registros da própria API) |
| 25/10/2026 | O estado dos sensores ganha avisos: Conectado, Sem sinal e Aguardando dados, com notificação quando um sensor para e quando volta. Os sensores passam a substituir a previsão do tempo no cálculo do risco |
| 28/10/2026 | O Chama passa a **ler a API externa dos sensores ESP32**. A pasta `docs/api-sensores` documenta uma versão melhorada dessa API |
| 06/11/2026 | Primeiro teste ponta a ponta. A API estava no ar, mas o banco dela no Supabase não respondia (veja a seção 5) |
| 13/11/2026 | O banco volta a funcionar e a integração é confirmada de novo |
| 19/11/2026 | A equipe decide separar a parte de sensores num app próprio, o **EcoGuard**, entregue como executável |
| 19/11/2026 | O EcoGuard é construído: sem login, banco local, visual novo tirado do logo, fluxo em três passos, rede de sensores e dados de exemplo |
| 19/11/2026 | Empacotamento: janela própria, executável (PyInstaller) e instalador (Inno Setup). O repositório do EcoGuard é criado no GitHub e a release 1.0 é publicada |
| 19/11/2026 | Primeiro guia da professora, em Word |
| 23/11/2026 | Correção: sensores apagados na API saem da lista "Sensores sem lugar". Entra a **atualização dentro do app** e sai a versão 1.1.0. O guia da professora é refeito, passo a passo, para quem não é da área |

## 3. Como a solução funciona

Há dois caminhos para uma leitura chegar ao app:

1. **Sensores do próprio Chama (`CHM-...`).** O aparelho envia a medição ao Chama por `POST /api/leituras`, junto com o código e um token. Foi a primeira versão e serviu para desenvolver e testar o resto. Pode ser simulada com `simulador_iot.py`.
2. **ESP32 do projeto.** O aparelho envia a medição a uma **API separada**, e o Chama **busca** as leituras de lá. Este é o caminho que o EcoGuard mantém.

O caminho 2, em passos:

1. O **ESP32** mede temperatura, umidade do ar e umidade do solo e envia um `POST /dados` à API, com `codigo_esp32`, `temperatura`, `umidade_ar` e `umidade_solo`.
2. A **API** (FastAPI, hospedada no Render) grava a leitura num banco **PostgreSQL no Supabase** e devolve os dados em `GET /dados`.
3. O app **nunca fala com o banco**, só com os endpoints da API. Em segundo plano, o servidor do app faz `GET /dados` (a cada 5 minutos no Chama e a cada 30 segundos no EcoGuard), ou quando a pessoa clica em "Buscar agora".
4. Cada leitura é **validada** (umidades de 0 a 100 %, temperatura de -20 a 70 °C, data não pode estar no futuro). Leituras quebradas ou impossíveis são descartadas.
5. As leituras boas são guardadas na tabela `leituras`, **sem duplicar**, e passam a alimentar o mapa, o estado do sensor e os avisos.

A busca roda numa thread separada, para a tela não travar enquanto a API acorda.

## 4. Recursos utilizados

**Aplicação**
- Python 3.12 e **Flask** (servidor e páginas).
- **Flask-SQLAlchemy / SQLAlchemy 2.0** (ORM) sobre **SQLite**.
- **requests** (chamadas à API), **python-dotenv** (variáveis de ambiente) e **Pillow** (imagens).
- HTML, CSS e JavaScript simples, com templates **Jinja2**. Instalável na tela inicial do celular (PWA).
- **Leaflet** para o mapa, com imagens de satélite da **Esri**.

**Sensores e API**
- **ESP32** com sensores de temperatura, umidade do ar e umidade do solo **[preencher: modelo exato dos sensores e do ESP32]**.
- API própria em **FastAPI** (Python), hospedada no **Render**, com banco **PostgreSQL** no **Supabase**. O repositório dela é `rodrigodosssantos/projeto-sensores-esp32`.

**Ferramentas de desenvolvimento**
- **Git e GitHub** para versionamento.
- **Claude Code** (assistente de programação com IA) para escrever, revisar e testar código, além de gerar a documentação. Os commits registram essa coautoria.
- Navegador emulando celular (390×844 e 360×640) para testar as telas, e PowerShell para rodar o app e consultar a API.

## 5. Problemas encontrados e como foram resolvidos

| Problema | Solução |
| --- | --- |
| Uma leitura de teste com **100 °C e umidade 0 %** estava gravada na API | O app valida cada leitura e descarta valores fora da faixa. A API melhorada (`docs/api-sensores`) também passa a recusar esses valores |
| A API do Render **demora cerca de 20 s para acordar** | A busca roda em segundo plano, com mensagem clara se demorar ou falhar. O app continua usando as leituras que já tem |
| O banco do Supabase **parou de responder** em 06/11 (erro de usuário não encontrado, projeto provavelmente pausado por inatividade) | Diagnóstico pelo endpoint `/teste-banco` da API. O banco foi restaurado e a integração voltou a funcionar em 13/11 |
| A mesma leitura poderia ser importada **duas vezes** | Cada leitura guarda o `id` que ela tem na API, com um índice único por sensor. Repetir a busca é seguro |
| A API **não diz quem é dono** de cada código de ESP32 | No app, vale quem cadastrar o código primeiro. A pasta `docs/api-sensores` traz o desenho de um token por aparelho, ainda não implementado |
| A API **não guarda localização** do sensor | A localização é informada no app, na hora de cadastrar. Na rede pública ela é arredondada a cerca de 1 km |
| O horário da API vem em UTC com fuso | O app converte para UTC sem fuso ao guardar e mostra "há quanto tempo" na tela |
| Dados de um usuário podiam aparecer para outro | Cada pessoa só enxerga e altera as próprias regiões e sensores. Na rede pública nunca saem token, código do aparelho, email ou nome do dono. No EcoGuard o problema deixa de existir: não há contas, só um perfil local |
| **(EcoGuard)** A segunda busca na API falhava com erro de duplicidade, porque a API atual ignora o filtro `desde_id` e devolve tudo | O app passou a pular qualquer leitura cujo `id` já foi importado. Três buscas seguidas foram testadas sem erro |
| **(EcoGuard)** Sensores apagados no banco da API continuavam na lista "Sensores sem lugar" | A cada 10 minutos (ou ao clicar em "Buscar agora") o app busca a lista inteira e tira da tela os sensores sem lugar que a API não devolve mais. Os já colocados no mapa ficam |
| **(EcoGuard)** O ambiente virtual copiado do Chama apontava para a pasta do Chama e instalou pacotes no projeto antigo | O ambiente virtual foi apagado e recriado dentro do EcoGuard |

## 6. Decisões de projeto

- **Integrar por API, não por banco.** O app só usa os endpoints. Não usa credenciais do Supabase, o que reduz o risco de segurança.
- **Guardar as leituras no próprio app.** Assim o mapa, os estados e os avisos funcionam igual para qualquer sensor, e o app continua mostrando o último dado se a API cair.
- **Privacidade por padrão.** Localização aproximada e nenhum dado pessoal na rede pública.
- **Documentar a API melhorada em vez de alterá-la sozinhos.** A API é de outro repositório, então a melhoria ficou como proposta, com passo a passo, para quem a mantém aplicar.

## 7. Testes realizados

- **Integração ponta a ponta** (06/11): numa cópia isolada do banco, foi criada uma conta, uma região e cadastrado o sensor `ESP32_TESTE_CHAMA`. A busca importou 1 leitura sozinha (27 °C, 45 % de umidade do ar, 50 % de umidade do solo).
- **Estado do sensor:** o sensor apareceu como "Sem sinal" porque a última leitura tinha mais de 30 minutos, o que é o comportamento esperado.
- **Resposta da API** conferida direto no `GET /dados` e no `/teste-banco`.
- **Celular:** todas as telas testadas sem rolagem lateral e sem erros de JavaScript.
- **Limitação:** a API em produção é a versão antiga e ignora os filtros (`limite`, `ordem`, `desde_id`). O app funciona assim, mas baixa todas as leituras a cada busca.

### No EcoGuard (19 a 23/11)

- **Busca real na API:** 94 leituras importadas e 6 códigos descobertos (`ESP32_001`, `ESP32_002`, `ESP32_003`, `ESP32_005`, `ESP32_TESTE_CHAMA` e `STRING`). Cadastro de sensor, "sem lugar", apagar propriedade e restaurar exemplos funcionaram.
- **Sem vazamento:** o código do aparelho não aparece nos sensores do mapa, só na lista "sem lugar".
- **Remoção de sensores sumidos da API:** testada com uma API simulada (de 4 códigos, sobraram só os 2 que a API ainda tinha).
- **Executável e instalador:** o `.exe` abre a janela própria, escolhe porta livre e encerra ao fechar. O instalador foi instalado, executado e desinstalado numa pasta de teste, e a atualização silenciosa por cima, com o app aberto, fechou e reabriu o programa sozinha.
- **Atualização no app:** testadas a comparação de versões, as travas de segurança (endereço fora do GitHub, pedido sem cabeçalho) e a parte do instalador.
- **Visual:** conferido por capturas de tela do mapa e das telas de propriedade e sensor.

## 8. Da parte de sensores ao EcoGuard

Para a entrega da extensão, a equipe precisava de algo menor que o Chama inteiro. O **EcoGuard** ficou só com:

- propriedades no mapa (ponto e raio, como no Chama);
- cadastro de sensores;
- visualização da rede de sensores.

Ficaram de fora relatos de incêndio, validação, cargos, time, alertas de fogo, previsão do tempo, área Aprenda e login. O EcoGuard é entregue como **executável para Windows**, usado pela professora e apresentado por crianças. Isso pediu uma interface muito simples, dados de exemplo e um modo demonstração.

Em 19/11 foi criada a pasta do EcoGuard como cópia do Chama e escrito o `CLAUDE.md`, que reúne o escopo, as decisões, os riscos do dia da apresentação e a ordem de trabalho.

## 9. O que foi feito no EcoGuard

- **Recomeço limpo.** O histórico do Git, o banco e os segredos do Chama foram descartados, e o projeto ganhou um repositório novo. Saíram relatos, validação, cargos, time, alertas, clima, Aprenda, login, administração e os sensores `CHM-`.
- **Sem conta.** Há um perfil local único. O banco (SQLite) fica em `%APPDATA%\EcoGuard`, nunca ao lado do programa.
- **Identidade visual nova**, tirada do logo do projeto: azul-marinho, verde-limão e azul-céu, fonte Nunito, botões de no mínimo 44 px e texto grande para projetor. O Leaflet e a fonte vão embutidos, então a interface abre sem internet.
- **Fluxo em três passos, sempre visível:** onde fica a propriedade, cadastro do sensor e mapa. Os estados dos sensores são **Funcionando**, **Sem sinal** e **Esperando**, e os erros dizem o que fazer.
- **Rede de sensores.** Todo código que a API devolve vira um sensor; os que ainda não têm lugar aparecem em "Sensores sem lugar", com o botão "Colocar no mapa", porque a API não guarda localização.
- **Dados de exemplo.** O app traz 5 propriedades e 10 sensores de mentira, marcados como "exemplo", com um botão discreto para restaurá-los. Eles ficam só no banco local e nunca são enviados à API.
- **Modo demonstração.** Sem internet o app abre e mostra os exemplos, com aviso claro. O mapa de satélite cai num mapa simples quadriculado. Quando a API está acordando, a tela avisa "Acordando os sensores...".
- **Executável e instalador.** O programa abre em janela própria (sem terminal), escolhe uma porta livre e encerra ao fechar a janela. O instalador é feito com Inno Setup, em português, **sem pedir administrador**.
- **Atualização dentro do app.** O app confere a última *release* do repositório no GitHub; se houver versão maior, mostra um aviso com o botão "Atualizar agora". Nada é baixado nem instalado sem clique, e o arquivo baixado é conferido (tamanho e SHA-256).
- **Guia da professora**, em Word, em duas páginas, com passo a passo para quem não é da área: teste na véspera, preparação do dia e tabela de problemas.
- **Repositório no GitHub** para a revisão da parte dos sensores pelo colega que mantém a API.

## 10. Limitações conhecidas e o que falta

- A API dos sensores **não tem autenticação por aparelho**, e o `POST /dados` é aberto a qualquer pessoa. No EcoGuard vale quem cadastrar o código primeiro, o que é aceitável num app local.
- A API gratuita **dorme** e o banco do Supabase gratuito **pausa** por inatividade. Os dois precisam ser conferidos antes de uma apresentação (o guia da professora explica como).
- A API atual ignora os filtros e devolve todas as leituras a cada busca. A versão melhorada (`docs/api-sensores`) ainda não foi publicada e depende do aceite de quem mantém a API.
- A API devolve códigos de teste (`ESP32_TESTE_CHAMA` e `STRING`) que aparecem na lista de sensores sem lugar até alguém apagá-los na própria API.
- O instalador **ainda não foi testado num Windows sem Python**. Ele também não é assinado, então o Windows mostra o aviso "protegeu o computador" (o guia ensina a passar por ele).
- A atualização dentro do app só funciona com o repositório **público**. Se ele ficar privado, a atualização é feita instalando o novo instalador por cima.
- O intervalo de envio do ESP32 é definido no firmware. O recomendado é a cada 10 minutos, e isso precisa ser confirmado.
- A posição do sensor mostrada no mapa é a que a criança clicou, sem arredondar a cerca de 1 km, porque o app é local e não há rede pública compartilhada.
