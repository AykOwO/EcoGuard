
from datetime import datetime
from typing import Literal
import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import psycopg


DATABASE_URL = os.getenv("DATABASE_URL")

# Chaves opcionais. Se a variavel NAO existir no Render, a rota continua aberta, como antes.
# Para proteger, crie a variavel no Render e mande o mesmo valor no cabecalho X-API-Key.
CHAVE_ESCRITA = os.getenv("CHAVE_ESCRITA")  # exigida em POST /dados (quem envia: os ESP32)
CHAVE_LEITURA = os.getenv("CHAVE_LEITURA")  # exigida em GET /dados (quem le: o painel / o EcoGuard)

print("DATABASE_URL configurada:", DATABASE_URL is not None)
print("POST /dados protegido por chave:", bool(CHAVE_ESCRITA))
print("GET /dados protegido por chave:", bool(CHAVE_LEITURA))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Para testes; restrinja ao domínio do painel em produção.
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


class DadosSensores(BaseModel):
    codigo_esp32: str = Field(min_length=4, max_length=32)
    temperatura: float = Field(ge=-40, le=85)  # graus Celsius
    umidade_ar: float = Field(ge=0, le=100)  # porcentagem
    umidade_solo: int = Field(ge=0, le=100)  # porcentagem


def conectar_banco():
    return psycopg.connect(DATABASE_URL)


def exigir_chave(chave_esperada):
    """Se a chave existir (variavel de ambiente), exige o mesmo valor no cabecalho X-API-Key.
    Se nao existir, deixa passar (comportamento antigo)."""
    def verificar(x_api_key: str | None = Header(None)):
        if not chave_esperada:
            return
        if not x_api_key or not secrets.compare_digest(x_api_key.encode(), chave_esperada.encode()):
            raise HTTPException(status_code=401, detail="Chave invalida ou ausente")
    return verificar


@app.get("/")
def inicio():
    return {
        "mensagem": "API dos sensores funcionando!"
    }


@app.get("/teste-banco")
def teste_banco():
    try:
        conexao = conectar_banco()
        conexao.close()

        return {
            "status": "ok",
            "mensagem": "Conexao com o banco funcionando!"
        }

    except Exception as erro:
        print("Erro ao conectar no banco:", erro)  # o detalhe fica so no log do Render
        return {
            "status": "erro",
            "mensagem": "Nao foi possivel conectar ao banco"
        }


@app.post("/dados", dependencies=[Depends(exigir_chave(CHAVE_ESCRITA))])
def receber_dados(dados: DadosSensores):
    print("Dados recebidos:")
    print(f"ESP32: {dados.codigo_esp32}")
    print(f"Temperatura: {dados.temperatura} °C")
    print(f"Umidade do ar: {dados.umidade_ar} %")
    print(f"Umidade do solo: {dados.umidade_solo} %")

    with conectar_banco() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                INSERT INTO public.leituras (
                    codigo_esp32,
                    temperatura,
                    umidade_ar,
                    umidade_solo
                )
                VALUES (%s, %s, %s, %s)
            """, (
                dados.codigo_esp32,
                dados.temperatura,
                dados.umidade_ar,
                dados.umidade_solo
            ))

    return {
        "status": "ok",
        "mensagem": "Dados recebidos e salvos no banco",
        "codigo_esp32": dados.codigo_esp32
    }


@app.get("/dados", dependencies=[Depends(exigir_chave(CHAVE_LEITURA))])
def listar_dados(
    codigo_esp32: str | None = None,  # so as leituras desse aparelho
    desde_id: int | None = Query(None, ge=0),  # so as leituras com id MAIOR que este
    desde: datetime | None = None,  # so as leituras a partir deste instante (ex.: 2026-10-28T12:00:00Z)
    limite: int = Query(1000, ge=1, le=5000),  # quantas leituras devolver, no maximo
    ordem: Literal["asc", "desc"] = "desc",  # desc = mais novas primeiro (como era antes)
):
    condicoes = []
    parametros = []

    if codigo_esp32:
        condicoes.append("codigo_esp32 = %s")
        parametros.append(codigo_esp32)

    if desde_id is not None:
        condicoes.append("id > %s")
        parametros.append(desde_id)

    if desde is not None:
        condicoes.append("data_hora >= %s")
        parametros.append(desde)

    onde = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
    direcao = "ASC" if ordem == "asc" else "DESC"  # so entra ASC ou DESC (nunca texto de fora)

    with conectar_banco() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    id,
                    codigo_esp32,
                    temperatura,
                    umidade_ar,
                    umidade_solo,
                    data_hora
                FROM public.leituras
                {onde}
                ORDER BY data_hora {direcao}, id {direcao}
                LIMIT %s
            """, parametros + [limite])

            resultados = cursor.fetchall()

    dados = []

    for linha in resultados:
        dados.append({
            "id": linha[0],
            "codigo_esp32": linha[1],
            "temperatura": linha[2],
            "umidade_ar": linha[3],
            "umidade_solo": linha[4],
            "data_hora": linha[5]
        })

    return dados
