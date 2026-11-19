# Melhorando a API dos sensores: passo a passo

Para quem vai mexer no repositório `rodrigodosssantos/projeto-sensores-esp32` e não tem muita prática com Git. Os arquivos prontos estão nesta pasta:

| Arquivo | O que é | Para onde vai no repositório |
|---|---|---|
| `main.py` | a API com as melhorias | substitui `api/main.py` |
| `indices.sql` | um comando para deixar as buscas rápidas | roda no Supabase (não vai para o GitHub se você não quiser) |
| `mudancas.diff` | só para **ler** o que mudou, linha a linha | não precisa usar |

## O que muda (e o que NÃO muda)

**Nada quebra.** Tudo o que é novo é opcional e a API continua respondendo do mesmo jeito para quem já a usa (o ESP32, o EcoGuard).

1. **`GET /dados` ganha filtros:** `?codigo_esp32=ESP32_001`, `?desde_id=10`, `?desde=2026-10-28T12:00:00Z`, `?limite=100`, `?ordem=asc`. Sem nenhum parâmetro, devolve o mesmo de antes (só limitado a 1000 leituras, as mais novas).
2. **`POST /dados` recusa leitura impossível** (temperatura fora de -40 a 85 °C, umidade fora de 0 a 100 %, código curto demais). Era assim que um teste com 100 °C entrou no banco.
3. **Chaves opcionais:** se você criar a variável `CHAVE_ESCRITA` (e/ou `CHAVE_LEITURA`) no Render, a rota passa a exigir o cabeçalho `X-API-Key`. Se não criar, tudo continua aberto como hoje.
4. **`/teste-banco` não mostra mais o servidor e o usuário do banco** quando dá erro.

Foi testado num banco de mentira (com os mesmos comandos SQL), incluindo tentativa de SQL injection, valores inválidos e as chaves.

## Passo 1: ter permissão para enviar o código

Você precisa de uma destas duas coisas. Pergunte ao Rodrigo qual prefere:

- **Ele te convida como colaborador** do repositório (GitHub > repositório > Settings > Collaborators). Aí você envia direto.
- **Você faz um fork e abre um Pull Request** (GitHub > botão *Fork*; depois de enviar suas mudanças ao seu fork, aparece o botão *Compare & pull request*). Ele só precisa clicar em *Merge*.

## Passo 2: baixar o projeto

No terminal (PowerShell), numa pasta onde você guarda projetos:

```powershell
git clone https://github.com/rodrigodosssantos/projeto-sensores-esp32.git
cd projeto-sensores-esp32
git switch -c filtros-e-seguranca
```

(Se fez um fork, troque a URL pela do **seu** fork.) O último comando cria uma "ramificação" para você mexer sem risco: o código principal continua intocado.

## Passo 3: colocar os arquivos novos

Copie `main.py` desta pasta por cima de `api\main.py` do projeto, e `indices.sql` para dentro de `api\`. Depois confira o que mudou:

```powershell
git status
git diff
```

Deve aparecer `api/main.py` modificado e `api/indices.sql` novo, e mais nada.

## Passo 4: enviar para o GitHub

```powershell
git add api/main.py api/indices.sql
git commit -m "Filtros no GET /dados, validacao no POST e chaves opcionais"
git push -u origin filtros-e-seguranca
```

Na página do repositório no GitHub vai aparecer um aviso amarelo com **Compare & pull request**. Clique, escreva o que mudou (pode copiar a lista de cima) e clique em **Create pull request**. Quando o Rodrigo (ou você, se tiver permissão) clicar em **Merge**, o código principal é atualizado.

## Passo 5: publicar no Render

Se o serviço do Render está ligado ao GitHub (ele costuma estar), ele publica sozinho depois do merge, em alguns minutos. Se não publicar: no painel do Render, abra o serviço e clique em **Manual Deploy > Deploy latest commit**.

## Passo 6: criar o índice no Supabase (uma vez)

Abra o projeto no Supabase, vá em **SQL Editor**, cole o conteúdo de `indices.sql` e clique em **Run**. É seguro repetir (`IF NOT EXISTS`).

## Passo 7: conferir que funcionou

Abra `https://projeto-sensores-esp32.onrender.com/docs` (a primeira vez demora uns 20 s) e teste:

- `GET /dados` com `codigo_esp32` = `ESP32_001` e `limite` = 5: deve devolver no máximo 5 leituras só desse aparelho.
- `GET /dados` com `ordem` = `asc`: a primeira da lista tem que ser a mais antiga.
- `GET /teste-banco`: deve dizer `"Conexao com o banco funcionando!"`.

O EcoGuard passa a usar os filtros sozinho; não precisa mexer nele.

## Passo 8 (depois, quando quiserem proteger): as chaves

**A ordem importa**, senão o ESP32 fica sem conseguir enviar:

1. **Primeiro** o código novo no ar (passos acima). Nada muda para ninguém.
2. **Depois**, no firmware do ESP32, mande o cabeçalho em cada envio. Enquanto a variável não existir no Render, o servidor ignora o cabeçalho, então é seguro fazer isso antes. No Arduino (`HTTPClient`):
   ```cpp
   http.addHeader("Content-Type", "application/json");
   http.addHeader("X-API-Key", "A_MESMA_CHAVE_QUE_VAI_NO_RENDER");
   ```
   Use **HTTPS** (`WiFiClientSecure`); sem isso a chave passa em texto puro pela rede.
3. **Só então**, no painel do Render > seu serviço > **Environment**, crie `CHAVE_ESCRITA` com um texto longo e aleatório. Para gerar um:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
4. Se quiserem proteger também a **leitura**: crie `CHAVE_LEITURA` no Render **depois** de colocar a mesma chave no EcoGuard (variável `ECOGUARD_SENSORES_API_CHAVE`). Se for ao contrário, o EcoGuard leva um erro 401 por alguns minutos.

**Nunca** coloque as chaves dentro do código nem no GitHub. Elas ficam só no Render (e no firmware / no EcoGuard).

## Se algo der errado

Desfazer é fácil: no GitHub, abra o Pull Request já aceito e clique em **Revert**. Ou, no terminal, `git revert <código do commit>` e `git push`.

## O que ainda não foi feito

- **Um token por aparelho** (cada ESP32 com a sua senha; um aparelho vazado não compromete os outros). É a evolução natural das chaves acima. O desenho e o código estão em `token-por-aparelho.md`, nesta pasta.
- Escolher uma lista de origens permitidas no CORS (hoje é `*`, o que é aceitável enquanto só se lê).
