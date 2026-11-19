# Processo de desenvolvimento da parte de sensores (do Chama ao EcoGuard)

Este documento conta como a parte de sensores foi construída, com as tecnologias usadas, os problemas encontrados e o que foi decidido em cada etapa. Ele vai até o ponto em que o **EcoGuard** passa a ser empacotado como executável. A partir daí, o trabalho continua a partir do `CLAUDE.md` e deste texto.

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

## 3. Como a solução funciona

Há dois caminhos para uma leitura chegar ao app:

1. **Sensores do próprio Chama (`CHM-...`).** O aparelho envia a medição ao Chama por `POST /api/leituras`, junto com o código e um token. Foi a primeira versão e serviu para desenvolver e testar o resto. Pode ser simulada com `simulador_iot.py`.
2. **ESP32 do projeto.** O aparelho envia a medição a uma **API separada**, e o Chama **busca** as leituras de lá. Este é o caminho que o EcoGuard mantém.

O caminho 2, em passos:

1. O **ESP32** mede temperatura, umidade do ar e umidade do solo e envia um `POST /dados` à API, com `codigo_esp32`, `temperatura`, `umidade_ar` e `umidade_solo`.
2. A **API** (FastAPI, hospedada no Render) grava a leitura num banco **PostgreSQL no Supabase** e devolve os dados em `GET /dados`.
3. O app **nunca fala com o banco**, só com os endpoints da API. Em segundo plano, o servidor do app faz `GET /dados` a cada 5 minutos, ou quando a pessoa toca em "Buscar agora".
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
| Dados de um usuário podiam aparecer para outro | Cada pessoa só enxerga e altera as próprias regiões e sensores. Na rede pública nunca saem token, código do aparelho, email ou nome do dono |

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

## 8. Da parte de sensores ao EcoGuard

Para a entrega da extensão, a equipe precisava de algo menor que o Chama inteiro. A ideia do **EcoGuard** é ficar só com:

- propriedades no mapa (ponto e raio, como no Chama);
- cadastro de sensores;
- visualização pública da rede de sensores.

Ficam de fora relatos de incêndio, validação, cargos, time, alertas de fogo, previsão do tempo, área Aprenda e login. O EcoGuard será entregue como **executável para Windows**, usado pela professora e apresentado por crianças. Isso pede uma interface muito simples, dados de exemplo (cerca de 5 propriedades e 10 sensores) e um modo demonstração.

Em 19/11 foi criada a pasta do EcoGuard como cópia do Chama e escrito o `CLAUDE.md`, que reúne o escopo, as decisões, os riscos do dia da apresentação e a ordem de trabalho.

## 9. Onde o documento termina

Este texto cobre o desenvolvimento até **a decisão e o planejamento do EcoGuard**. Ficam para a continuação:

1. Remover o que não pertence ao EcoGuard, tirar o login e renomear o projeto.
2. Criar a interface para crianças e os dados de exemplo.
3. Empacotar o executável com PyInstaller, testar num Windows limpo e preparar o guia da professora.
4. Atualizar este documento com o que foi feito nessas etapas.

## 10. Limitações conhecidas

- A API dos sensores **não tem autenticação por aparelho**, e o `POST /dados` é aberto a qualquer pessoa.
- A API gratuita **dorme** e o banco do Supabase gratuito **pausa** por inatividade. Os dois precisam ser conferidos antes de uma apresentação.
- Os textos educativos do Chama e as faixas da regra dos 30 são rascunho e não foram validados por bombeiros. No EcoGuard essa parte não entra.
