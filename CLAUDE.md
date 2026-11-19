# EcoGuard: briefing do projeto

Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele substitui o contexto da conversa anterior, onde o projeto nasceu como cópia do **Chama**.

## 1. O que é

O EcoGuard é a parte de **sensores** do Chama, separada num app simples, entregue como **executável para Windows**. Foi feito para um **projeto de extensão** da faculdade. No dia da entrega, a **professora** abre o programa e as **crianças** apresentam o que foi desenvolvido, usando o app.

O que a pessoa faz no app:
1. Marca uma **propriedade** no mapa (ponto e raio).
2. **Cadastra sensores** nela (ESP32).
3. **Vê no mapa a rede de sensores**: todos os que estão na API dos sensores.

Não faz parte do EcoGuard: relatos de incêndio, validação, cargos, time, alertas de fogo, regra dos 30, previsão do tempo, área Aprenda, login.

## 2. Quem usa e o que isso exige

- **Crianças** apresentando, **professora** acompanhando até o fim. Interface amigável, texto grande, poucos botões, linguagem simples, ícones e cores fortes. Pensada para projetor ou tela de sala de aula.
- Computador **Windows com internet**, e dá para **instalar** software. Não assuma permissão de administrador sem confirmar.
- **Prazo:** o dono quer terminar **até amanhã**. Priorize o que faz a apresentação funcionar (seção 9) e deixe o resto como melhoria.

## 3. Decisões já tomadas

| Tema | Decisão |
| --- | --- |
| Formato | Executável Windows (PyInstaller). Dois cliques e abre. Sem terminal, sem `pip`, sem editar `.env` |
| Login | **Sem conta.** Um perfil local único. Remover email e senha, bloqueio de login e termos de conta |
| Sensores | Só **ESP32 do projeto**, lidos pela API. Remover os sensores `CHM-` (`/api/leituras`, token do aparelho, `simulador_iot.py`) |
| Rede pública | Mostra **todos os sensores que a API tem**. A opção "privado" fica só como melhoria, se der tempo |
| Clima | Remover `clima.py` e a Open-Meteo. O mapa mostra só as leituras dos sensores |
| Mapa | Satélite da Esri, como hoje. Marcar o local **clicando no mapa** (GPS é só um extra) |
| Hospedagem | Nenhuma. Tudo roda no computador. A API dos sensores continua no Render |
| Banco | SQLite local, numa pasta do usuário (`%APPDATA%\EcoGuard`), nunca ao lado do `.exe` |

## 4. Dados de demonstração (obrigatório)

Para o mapa não aparecer vazio, o app já vem com **5 propriedades de exemplo e cerca de 10 sensores**, espalhados em lugares diferentes, com leituras de exemplo. No dia, as crianças **adicionam uma propriedade e um sensor novos** ao vivo.

- Os sensores de exemplo são **locais**. Marque-os na tela como "exemplo" para ninguém achar que são reais. **Não grave dados falsos na API real** (o `POST /dados` é aberto e isso suja o banco do Supabase).
- Crie um comando ou botão discreto para **restaurar os exemplos**, caso alguém apague tudo.
- Sem internet, o app precisa abrir mesmo assim e mostrar os exemplos (modo demonstração).

## 5. A API dos sensores

- URL: `https://projeto-sensores-esp32.onrender.com`. Feita em FastAPI, banco PostgreSQL no Supabase. O app **nunca** fala com o banco, só com os endpoints.
- `GET /dados` devolve uma lista com `id`, `codigo_esp32`, `temperatura`, `umidade_ar`, `umidade_solo`, `data_hora` (UTC com fuso). `POST /dados` recebe `codigo_esp32`, `temperatura`, `umidade_ar`, `umidade_solo` (sem `id` nem `data_hora`).
- Códigos conhecidos hoje: `ESP32_001` e `ESP32_TESTE_CHAMA`. O `ESP32_001` tem uma leitura de teste de 100 °C, que o app descarta pela validação.
- **A API não guarda localização.** Por isso um sensor só aparece no mapa depois que alguém diz onde ele está. Decisão: o app lista **todos os códigos** que a API devolve. Os que ainda não têm local aparecem numa lista "Sensores sem lugar", com o botão **Colocar no mapa**.
- A API **acorda em cerca de 20 s** (Render gratuito) e o banco dela já **pausou** uma vez (Supabase). No dia, isso é o maior risco. Veja a seção 8.
- Já existe no repositório a integração pronta em `app.py` (`sincronizar_sensores_externos`, busca em segundo plano, validação das leituras, mensagens de erro em português). **Reaproveite, não reescreva.** Os campos `Dispositivo.origem` e `Leitura.externo_id` e o índice único contra leitura duplicada continuam úteis.
- `docs/api-sensores/` tem uma versão melhorada da API (filtros, validação, chaves opcionais), **ainda não publicada**. Não é necessária para a apresentação. O app funciona com a API atual, só baixa mais dados.

## 6. O sensor físico no dia

O ideal é o ESP32 estar ligado e enviando para a API durante a apresentação.

- Descobrir **de quanto em quanto tempo** o firmware envia (pergunte ao dono). O app só considera "Conectado" uma leitura de menos de 30 minutos. Para a demonstração, reduza o intervalo de busca para cerca de **30 segundos** e deixe o botão **Buscar agora** bem visível.
- O código do aparelho (como `ESP32_001`) é o que as crianças digitam para cadastrar o sensor. Deixe a tela ensinar onde ele está.
- A API **não tem token por aparelho**: vale quem cadastrar o código primeiro. Para este app local isso é aceitável. Registre como limitação no README.

## 7. Interface para crianças

- Fluxo em três passos, sempre visível: **1. Onde fica a sua propriedade. 2. Cadastre o sensor. 3. Veja o mapa.**
- Estados do sensor com palavras simples: **Funcionando**, **Sem sinal**, **Esperando**. Nada de "origem", "token", "api_externa".
- Erros que dizem o que fazer ("Sem internet. Confira o Wi-Fi.").
- Aviso ao cadastrar: **não use endereço de casa nem sobrenome** nos nomes. A localização que aparece na rede é **aproximada** (arredondada a cerca de 1 km), como já faz o app.
- Nunca mostrar na rede o código do aparelho, o token ou dados de quem cadastrou.
- Visual **novo**, não o "brasa e cinza" do Chama. O nome sugere algo verde e natural. Botões de no mínimo 44 px, fonte grande, bom contraste.
- Trocar o nome **em todo lugar**: título, manifesto, ícones, logo (`templates/_logo.html`), textos, cookie e nome do banco. Ao final, buscar a palavra "Chama" no projeto para achar o que sobrou.

## 8. Riscos do dia e como reduzir

| Risco | O que fazer |
| --- | --- |
| API dormindo (cerca de 20 s) | Tela "acordando os sensores..." amigável. No guia da professora: abrir a API 10 minutos antes |
| Supabase pausado | Passo no guia: testar `/teste-banco` na véspera. Se der erro, restaurar o projeto no painel do Supabase |
| Sem internet | Modo demonstração com os exemplos. Mapa de satélite não carrega sem rede: ter um mapa simples de reserva |
| Antivírus ou SmartScreen barrando o `.exe` | Preferir PyInstaller em **pasta** (`--onedir`) com instalador (Inno Setup) em vez de arquivo único. Testar num computador limpo |
| Porta 5000 ocupada | O app escolhe outra porta livre sozinho |
| Janela do terminal assustando | Sem console (`--noconsole`). Abrir o app numa janela própria (pywebview) ou no navegador padrão |
| Fechar errado e perder dados | Banco em `%APPDATA%`, gravado a cada ação |

## 8.1 Empacotamento (detalhes)

- Os caminhos de `templates/` e `static/` precisam funcionar dentro do executável (`sys._MEIPASS`). O banco e a chave de sessão **não** ficam dentro do pacote.
- O app deve: subir o servidor em porta livre, abrir a janela sozinho e encerrar tudo quando a janela fechar.
- Gerar um **ícone** do app e um atalho na área de trabalho.
- Entregar também um **guia de uma página**, impresso, para a professora: como abrir, o que fazer se der erro, o que testar na véspera.

## 9. Ordem de trabalho (pensando em terminar até amanhã)

**Antes de tudo:** a pasta foi copiada do Chama. Ela traz `.env`, `chama.db`, a pasta `instance/` (com contas e chave de sessão) e o histórico do Git do Chama. **Não leve nada disso adiante.** Crie um repositório novo, ou apague o `.git` e comece limpo, e confirme que `.env` e `instance/` estão no `.gitignore`.

Um commit por etapa, rodando o app a cada uma:

1. **Remover o que sai.** Liste antes o que vai apagar e só então apague: relatos, validação, cargos, time, alertas de fogo, clima, Aprenda, login, `admin.py`, `conteudo.py`, `demo_fotos/`, sensores `CHM-`. Confira rotas e telas quebradas.
2. **Sem login.** Perfil local único; tirar `/entrar`, cadastro e perfil de conta.
3. **Renomear** para EcoGuard e criar a identidade visual nova.
4. **Fluxo das crianças** (seção 7): propriedade, sensor, mapa.
5. **Rede de sensores** com todos os da API, lista "sem lugar", exemplos e botão restaurar.
6. **Modo demonstração e erros amigáveis** (internet, API dormindo).
7. **Empacotar** (PyInstaller, ícone, instalador) e **testar num Windows limpo**.
8. **README e guia da professora.**

Se o tempo apertar, o mínimo para apresentar é: 1, 2, 3, 4, 5 e 7. O resto vira melhoria.

## 10. Como saber que está pronto

- [ ] O instalador funciona num Windows sem Python.
- [ ] Abre com dois cliques, sem terminal, e mostra a tela inicial.
- [ ] Já vêm 5 propriedades e cerca de 10 sensores de exemplo no mapa.
- [ ] Uma criança cadastra uma propriedade e um sensor novo em menos de 2 minutos, sem ajuda.
- [ ] O sensor `ESP32_001` (ou o físico do dia) aparece com leituras reais da API.
- [ ] Sem internet, o app abre e mostra os exemplos, com um aviso claro.
- [ ] Nenhum texto mostra "Chama", "token", "origem" ou código técnico.
- [ ] Nada de endereço, nome de pessoa ou código do aparelho aparece na rede.
- [ ] README e guia de uma página para a professora prontos.

## 11. Perguntas que ainda estão em aberto (pergunte ao dono)

1. De quanto em quanto tempo o ESP32 físico envia os dados?
2. O computador do dia vai estar na mesma rede Wi-Fi do ESP32? (Não é necessário: o ESP32 envia à API pela internet.)
3. A API melhorada (`docs/api-sensores`) será publicada antes ou depois? Precisa do aceite do Rodrigo.
4. Quem mantém a API e o banco dos sensores depois da entrega?
5. Qual o nome e a instituição que devem aparecer no app (rodapé, créditos)?
