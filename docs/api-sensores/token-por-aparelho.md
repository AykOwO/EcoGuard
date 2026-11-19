# Token por aparelho (fase 2, para depois)

Hoje, com a chave única, todos os ESP32 compartilham o mesmo segredo: se um vazar, vale para todos. Na fase 2, cada aparelho tem o seu token.
O servidor guarda só o **hash** do token, e dá para desativar um aparelho sozinho.

```sql
CREATE TABLE public.aparelhos (
  codigo_esp32 text PRIMARY KEY,
  token_hash   text NOT NULL,          -- sha256 do token (nunca guarde o token em si)
  ativo        boolean NOT NULL DEFAULT true,
  criado_em    timestamptz NOT NULL DEFAULT now()
);
```

Gerar o token de um aparelho novo (uma vez por aparelho; grave o token no firmware, ele não é mostrado de novo):

```python
import hashlib, secrets
token = secrets.token_urlsafe(24)
print("token (grave no aparelho):", token)
print("INSERT INTO public.aparelhos (codigo_esp32, token_hash) VALUES ('ESP32_002', '%s');" % hashlib.sha256(token.encode()).hexdigest())
```

No `POST /dados`, o aparelho manda `Authorization: Bearer <token>` e a API confere **para o código que veio no corpo**:

```python
import hashlib, secrets
from fastapi import Header, HTTPException

@app.post("/dados")
def receber_dados(dados: DadosSensores, authorization: str | None = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    with conectar_banco() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT token_hash, ativo FROM public.aparelhos WHERE codigo_esp32 = %s", (dados.codigo_esp32,))
            linha = cursor.fetchone()
    enviado = hashlib.sha256(token.encode()).hexdigest()
    esperado = linha[0] if linha else "0" * 64           # compara sempre, para não revelar quais códigos existem
    if not token or not secrets.compare_digest(enviado, esperado) or not (linha and linha[1]):
        raise HTTPException(status_code=401, detail="Aparelho nao autorizado")
    ...  # grava a leitura, como hoje
```

Desativar um aparelho: `UPDATE public.aparelhos SET ativo = false WHERE codigo_esp32 = 'ESP32_002';`

Nos ESP32: HTTPS (`WiFiClientSecure`) e o cabeçalho `Authorization: Bearer <token>`. Quando a fase 2 estiver no ar, a chave única (`CHAVE_ESCRITA`) pode ser aposentada.
