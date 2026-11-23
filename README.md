# EcoGuard

> **Monitorando hoje, preservando sempre.**

O EcoGuard é um programa para **Windows** que mostra no mapa a rede de sensores ESP32 do projeto de extensão. Foi feito para as crianças apresentarem o que construíram, com a professora acompanhando.

Em três passos, sempre visíveis no topo da tela:

1. **Onde fica a sua propriedade.** Clique no mapa e escolha o tamanho (ponto e raio).
2. **Cadastre o sensor.** Digite o código do aparelho (ex.: `ESP32_001`) e diga onde ele está.
3. **Veja o mapa.** Todos os sensores da API aparecem como *Funcionando*, *Sem sinal* ou *Esperando*.

Não precisa de conta, de login nem de servidor: tudo roda no computador. Só os dados dos sensores vêm da internet.

## Como rodar (para quem desenvolve)

Precisa de Python 3.12 ou mais novo.

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py        # abre em http://127.0.0.1:5000
```

O banco é criado sozinho na primeira vez, em `%APPDATA%\EcoGuard\ecoguard.db` (nunca ao lado do programa). Para testar sem mexer nos seus dados: `$env:ECOGUARD_DADOS="C:\temp\eg"`.

## Gerar o executável e o instalador

```powershell
.venv\Scripts\pip install pywebview pyinstaller
winget install JRSoftware.InnoSetup        # uma vez só
powershell -ExecutionPolicy Bypass -File tools\gerar_exe.ps1
```

Isso cria `dist\EcoGuard\EcoGuard.exe` (pasta, sem console) e `instalador\Instalar-EcoGuard.exe`. O instalador **não pede administrador** (instala para o usuário atual), cria o atalho na área de trabalho e fala português. O `EcoGuard.exe` escolhe sozinho uma porta livre, abre a janela própria (pywebview/WebView2) e encerra tudo quando a janela fecha. Se a janela não abrir, usa o navegador padrão.

### Atualização do programa

- Rodar o `Instalar-EcoGuard.exe` novo **por cima** atualiza o programa, sem desinstalar. O atalho e os dados (`%APPDATA%\EcoGuard`) continuam.
- Dentro do app: ao abrir (e a cada 6 horas) ele olha a última *release* do repositório no GitHub. Se a versão for maior que a instalada (`versao.py`), aparece o aviso **"Tem uma versão nova"** com o botão **Atualizar agora**. Nada é baixado nem instalado sem clique. O instalador baixado é conferido (tamanho e SHA-256) e roda em segundo plano; o app fecha e abre de novo sozinho.
- Funciona só com o repositório **público** (o app não tem chave para ler releases de repositório privado) e só no programa instalado. Sem internet, o aviso simplesmente não aparece.
- **Para lançar uma versão nova:** aumente `VERSAO` em `versao.py`, faça o commit e rode `powershell -ExecutionPolicy Bypass -File tools\gerar_exe.ps1 -Publicar`.
- A primeira vez que o app com atualização chegar a um computador precisa ser instalada à mão (versões antes da 1.1.0 não sabem se atualizar).

> Falta testar o instalador num Windows limpo, sem Python (CLAUDE.md, etapa 7). O guia de uma página para a professora está em `docs/Guia-da-professora.docx`.

## Dados de demonstração

Na primeira vez o app já traz **5 propriedades e 10 sensores de exemplo**, espalhados pelo Brasil, com leituras de mentira (um deles "sem sinal", outro "esperando"). Eles aparecem com borda tracejada e a palavra *exemplo*.

- Os exemplos são **só locais**: nunca são enviados à API dos sensores.
- O botão discreto **Restaurar exemplos** (canto do painel do mapa) traz os exemplos de volta. O que a turma cadastrou não é apagado.
- Sem internet, o app abre do mesmo jeito e mostra os exemplos, com um aviso. O mapa de satélite precisa de rede; sem ela aparece um mapa simples quadriculado.

## Sensores reais (API do projeto)

A API (`https://projeto-sensores-esp32.onrender.com`, FastAPI + Supabase no Render) guarda as leituras que os ESP32 enviam. O EcoGuard **nunca fala com o banco dela**, só com os endpoints:

- `GET /dados` devolve `id`, `codigo_esp32`, `temperatura`, `umidade_ar`, `umidade_solo`, `data_hora` (UTC).
- A cada **30 segundos** o app busca as leituras novas em segundo plano. O botão **Buscar agora** força uma busca.
- **Todo código** que a API devolve vira um sensor. Os que ainda não têm lugar aparecem em **Sensores sem lugar**, com o botão *Colocar no mapa*, porque a API não guarda localização.
- Leituras fora da faixa (temperatura de -20 a 70 °C, umidades de 0 a 100 %) são descartadas, como o teste de 100 °C do `ESP32_001`.
- **Intervalo do ESP32:** é definido no firmware do aparelho. O recomendado é enviar **a cada 10 minutos**: assim "Funcionando" (30 minutos) tolera até duas leituras perdidas. Para a apresentação dá para reduzir (ex.: 1 minuto) e voltar depois.
- Se alguém apagar um sensor no banco da API, ele sai da lista "Sensores sem lugar" na próxima conferência completa (no máximo 10 minutos; o botão **Buscar agora** confere na hora). Sensores já colocados no mapa ficam, e as leituras antigas deles também.
- Estados: **Funcionando** (leitura de menos de 30 minutos), **Sem sinal** (mais antiga), **Esperando** (nunca enviou).
- A API gratuita do Render **dorme** e leva cerca de 20 s para acordar. O app mostra "Acordando os sensores..." e tenta de novo sozinho.

Configuração opcional por variáveis de ambiente: `ECOGUARD_SENSORES_API` (URL; vazio desliga a busca), `ECOGUARD_SYNC_S` (intervalo, padrão 30), `ECOGUARD_SENSORES_API_CHAVE` (enviada em `X-API-Key`, para quando a API passar a exigir chave).

### Limitações conhecidas

- **A API não tem token por aparelho.** Nada prova quem é o dono de `ESP32_001`: vale quem cadastrar o código primeiro. Para este app local isso é aceitável. A proposta de token está em `docs/api-sensores/token-por-aparelho.md`.
- A API atual devolve **todas** as leituras a cada busca (ela ignora o filtro `desde_id`). Funciona, só baixa mais dados. A versão melhorada, com filtros, está em `docs/api-sensores/` e **ainda não foi publicada**.
- Os nomes e a posição são digitados pela turma. O aviso na tela pede para **não usar endereço de casa nem sobrenome**.
- O programa só aceita conexões do próprio computador (`127.0.0.1`) e exige um cabeçalho nas escritas, para que outra página aberta no navegador não consiga mexer nos dados.

## Estrutura

| Arquivo | O que faz |
| --- | --- |
| `app.py` | Servidor Flask: telas, rotas `/api/...` e a busca dos sensores em segundo plano |
| `banco.py` | Modelos (propriedades, sensores, leituras) e a pasta de dados em `%APPDATA%\EcoGuard` |
| `exemplos.py` | Os 5 lugares e 10 sensores de exemplo, e o "restaurar" |
| `templates/`, `static/` | Telas (`mapa`, `propriedade`, `sensor`), CSS, JS, Leaflet e fonte embutidos (funcionam sem internet) |
| `tools/gerar_icones.py` | Gera os ícones (`static/img/`) a partir de `static/img/logo-original.jpg` |
| `docs/` | A API melhorada dos sensores e o histórico de desenvolvimento |

## Identidade visual

Tirada do logo (`static/img/logo-original.jpg`): azul-marinho `#061E38`, verde-limão `#8AD321`, azul-céu `#3BB8FB`, ciano `#46F0FF` e um toque de laranja `#FD8C14`. Fonte Nunito. Botões de no mínimo 44 px e texto grande, pensado para projetor.

Créditos: **Cometa Charuri** (do logo).
