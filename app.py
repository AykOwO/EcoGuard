"""
EcoGuard: servidor local (Flask). Roda no computador, sem login e sem hospedagem.

Telas
  /              3. Veja o mapa: propriedades e a rede de sensores
  /propriedade   1. Onde fica a sua propriedade (clique no mapa e escolha o tamanho)
  /sensor        2. Cadastre o sensor (ESP32) e diga onde ele está

Os sensores ESP32 enviam as leituras para a API do projeto (FastAPI + Supabase, no Render). O EcoGuard NÃO fala com o
banco dela: busca GET /dados em segundo plano e guarda as leituras no banco local (%APPDATA%\\EcoGuard).
Sem internet, o app abre do mesmo jeito e mostra os exemplos (modo demonstração).
"""
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask, jsonify, render_template, request
from sqlalchemy import func, select

from banco import Leitura, Propriedade, Sensor, agora_utc, db, init_db, ultimas_leituras
from exemplos import garantir_exemplos, renovar_leituras, restaurar_exemplos

NOME = "EcoGuard"
# Dentro do executável (PyInstaller), templates e static ficam em sys._MEIPASS.
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

SENSOR_VALIDO_MIN = 30   # leitura com menos que isso = "Funcionando"
RAIO_PROPRIEDADE = (50, 30_000)

app = Flask(__name__, template_folder=os.path.join(BASE, "templates"), static_folder=os.path.join(BASE, "static"))
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
init_db(app)
with app.app_context():
    garantir_exemplos()


def erro(msg, status=400):
    return jsonify({"erro": msg}), status


def iso_utc(dt):
    """datetime UTC (sem fuso, como o banco guarda) -> '2026-09-23T14:03:00Z'"""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


@app.before_request
def _proteger():
    # Toda escrita via JavaScript manda este cabeçalho. Outro site aberto no navegador não consegue mandá-lo,
    # então ninguém de fora mexe nos dados do programa pelo endereço local.
    if request.method in ("POST", "PATCH", "PUT", "DELETE") and request.headers.get("X-EcoGuard") != "1":
        return erro("Requisição inválida.", 403)


@app.after_request
def _sem_cache(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------- páginas
@app.get("/")
def pg_mapa():
    return render_template("mapa.html", passo=3)


@app.get("/propriedade")
def pg_propriedade():
    return render_template("propriedade.html", passo=1)


@app.get("/sensor")
def pg_sensor():
    return render_template("sensor.html", passo=2)


@app.errorhandler(404)
def nao_encontrado(_e):
    if request.path.startswith("/api/"):
        return erro("Não encontrado.", 404)
    return render_template("erro.html", passo=0, titulo="Página não encontrada",
                           texto="Esse endereço não existe. Volte para o mapa."), 404


# ---------------------------------------------------------------- estado do sensor
def estado_sensor(ultima):
    """esperando = nunca enviou · funcionando = leitura recente · sem_sinal = parou de enviar."""
    if not ultima:
        return "esperando"
    return "funcionando" if agora_utc() - ultima.recebido_em < timedelta(minutes=SENSOR_VALIDO_MIN) else "sem_sinal"


def leitura_dict(l):
    if not l:
        return None
    return {"temperatura": l.temperatura, "umidade_ar": l.umidade_ar, "umidade_solo": l.umidade_solo, "em": iso_utc(l.recebido_em)}


def sensor_dict(s, ultima):
    """Sensor como a tela mostra. O código do aparelho só sai para os sensores sem lugar (a pessoa precisa dele para cadastrar)."""
    d = {"id": s.id, "nome": s.nome or "Sensor novo", "estado": estado_sensor(ultima), "exemplo": bool(s.exemplo),
         "lat": s.lat, "lon": s.lon, "propriedade_id": s.propriedade_id, "leitura": leitura_dict(ultima)}
    if s.propriedade_id is None:
        d["codigo"] = s.codigo
    return d


def propriedade_dict(p):
    return {"id": p.id, "nome": p.nome, "lat": p.lat, "lon": p.lon, "raio_m": p.raio_m, "exemplo": bool(p.exemplo)}


# ---------------------------------------------------------------- API: mapa
@app.get("/api/mapa")
def api_mapa():
    sensores = db.session.scalars(select(Sensor).order_by(Sensor.id)).all()
    ultimas = ultimas_leituras([s.id for s in sensores])
    props = db.session.scalars(select(Propriedade).order_by(Propriedade.id)).all()
    dicts = [sensor_dict(s, ultimas.get(s.id)) for s in sensores]
    no_mapa = [d for d in dicts if d["propriedade_id"] is not None and d["lat"] is not None]
    return jsonify({
        "propriedades": [propriedade_dict(p) for p in props],
        "sensores": no_mapa,
        "sem_lugar": [d for d in dicts if d["propriedade_id"] is None],
        "status": status_api(),
    })


# ---------------------------------------------------------------- API: propriedades
def ler_ponto_raio(dados):
    """Valida lat, lon e raio_m. Retorna (lat, lon, raio) ou uma mensagem de erro."""
    try:
        lat, lon, raio = float(dados.get("lat")), float(dados.get("lon")), float(dados.get("raio_m"))
    except (TypeError, ValueError):
        return "Clique no mapa para marcar o lugar."
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return "Esse ponto está fora do mapa."
    if not RAIO_PROPRIEDADE[0] <= raio <= RAIO_PROPRIEDADE[1]:
        return f"O tamanho precisa ficar entre {RAIO_PROPRIEDADE[0]} m e {RAIO_PROPRIEDADE[1] // 1000} km."
    return lat, lon, round(raio)


@app.post("/api/propriedades")
def api_propriedade_criar():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome") or "").strip()
    if not nome:
        return erro("Dê um nome para a propriedade. Ex.: Sítio Boa Vista.")
    p = ler_ponto_raio(dados)
    if isinstance(p, str):
        return erro(p)
    prop = Propriedade(nome=nome[:60], lat=p[0], lon=p[1], raio_m=p[2])
    db.session.add(prop)
    db.session.commit()
    return jsonify(propriedade_dict(prop)), 201


@app.delete("/api/propriedades/<int:pid>")
def api_propriedade_apagar(pid):
    prop = db.session.get(Propriedade, pid)
    if prop:
        for s in list(prop.sensores):
            if s.exemplo:
                db.session.delete(s)            # exemplo some junto
            else:
                s.propriedade_id = s.lat = s.lon = None   # sensor real volta para "sem lugar"
        db.session.delete(prop)
        db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- API: sensores
CODIGO_RE = re.compile(r"^[A-Z0-9_-]{4,32}$")   # ESP32_001


@app.post("/api/sensores")
def api_sensor_cadastrar():
    """Cadastra um sensor numa propriedade (ou coloca no mapa um que a API já conhece e ainda não tinha lugar)."""
    dados = request.get_json(silent=True) or {}
    codigo = re.sub(r"\s+", "", str(dados.get("codigo") or "")).upper()
    nome = str(dados.get("nome") or "").strip()
    if not CODIGO_RE.match(codigo):
        return erro("Confira o código do aparelho. Ele tem letras e números, como ESP32_001.")
    if codigo.startswith("EXEMPLO-"):
        return erro("Esse código é de um sensor de exemplo. Use o código do seu aparelho.")
    if not nome:
        return erro("Dê um nome para o sensor. Ex.: Sensor do pasto.")
    prop = db.session.get(Propriedade, dados.get("propriedade_id")) if isinstance(dados.get("propriedade_id"), int) else None
    if not prop:
        return erro("Escolha a propriedade onde o sensor está.")
    try:
        lat, lon = float(dados.get("lat", prop.lat)), float(dados.get("lon", prop.lon))
    except (TypeError, ValueError):
        return erro("Clique no mapa para mostrar onde o sensor está.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return erro("Esse ponto está fora do mapa.")

    s = db.session.scalar(select(Sensor).where(Sensor.codigo == codigo))
    if s and s.propriedade_id is not None:
        return erro("Esse sensor já está no mapa.", 409)
    if not s:
        s = Sensor(codigo=codigo)
        db.session.add(s)
    s.nome, s.propriedade_id, s.lat, s.lon = nome[:60], prop.id, lat, lon
    db.session.commit()
    iniciar_sincronizacao(forcar=True)   # já busca as leituras desse aparelho, sem esperar o intervalo
    return jsonify(sensor_dict(s, ultimas_leituras([s.id]).get(s.id))), 201


@app.delete("/api/sensores/<int:sid>")
def api_sensor_apagar(sid):
    s = db.session.get(Sensor, sid)
    if s:
        if s.exemplo:
            db.session.delete(s)
        else:
            s.propriedade_id = s.lat = s.lon = None   # volta para "sem lugar": a API continua mandando as leituras dele
        db.session.commit()
    return jsonify({"ok": True})


@app.post("/api/exemplos/restaurar")
def api_exemplos_restaurar():
    restaurar_exemplos()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- API: endereço (Nominatim / OpenStreetMap)
_nominatim_trava = threading.Lock()
_nominatim_ultimo = [0.0]


@app.get("/api/local")
def api_buscar_local():
    q = (request.args.get("q") or "").strip()
    if len(q) < 3:
        return jsonify([])
    # Política de uso do Nominatim: no máximo 1 pedido por segundo e User-Agent identificado (sem dados de ninguém).
    with _nominatim_trava:
        espera = 1.0 - (time.time() - _nominatim_ultimo[0])
        if espera > 0:
            time.sleep(espera)
        _nominatim_ultimo[0] = time.time()
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", timeout=8, headers={"User-Agent": "EcoGuard/1.0"},
                         params={"q": q, "limit": 5, "format": "json", "accept-language": "pt-BR", "countrycodes": "br"})
        r.raise_for_status()
        itens = r.json()
    except Exception:
        return erro("A busca não funcionou agora. Arraste o mapa até o lugar.", 503)
    return jsonify([{"nome": i["display_name"], "lat": float(i["lat"]), "lon": float(i["lon"])} for i in itens])


# ---------------------------------------------------------------- sensores ESP32 (API do projeto)
SENSORES_API = os.environ.get("ECOGUARD_SENSORES_API", "https://projeto-sensores-esp32.onrender.com").strip().rstrip("/")
SENSORES_API_CHAVE = os.environ.get("ECOGUARD_SENSORES_API_CHAVE", "").strip()   # para quando a API passar a exigir chave de leitura
SENSORES_SYNC_S = int(os.environ.get("ECOGUARD_SYNC_S") or 30)                   # de quanto em quanto tempo busca leituras novas
FAIXAS_LEITURA = {"umidade_ar": (0, 100), "umidade_solo": (0, 100), "temperatura": (-20, 70)}
_sync = {"inicio": 0.0, "fim": None, "executando": False, "ok": None, "tipo_erro": None, "novas": 0}
_trava_sync = threading.Lock()

MENSAGENS = {
    "acordando": "Acordando os sensores... Isso pode levar até 20 segundos.",
    "sem_internet": "Sem internet. Confira o Wi-Fi. Enquanto isso, você vê os exemplos.",
    "demorou": "Os sensores estão demorando para responder. Eles podem estar acordando. Tente de novo em instantes.",
    "erro": "Os sensores não responderam agora. Peça ajuda para a professora.",
}


def classificar_erro(e):
    """Tipo do erro, em palavras que a tela entende (o detalhe técnico vai só para o log)."""
    if isinstance(e, (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout)):
        return "demorou"
    if isinstance(e, requests.exceptions.ConnectionError):
        return "sem_internet"
    return "erro"


def status_api():
    if not SENSORES_API:
        return {"estado": "desligada", "mensagem": "A busca de sensores está desligada. Você vê só os exemplos."}
    if _sync["executando"] and not _sync["ok"]:
        return {"estado": "acordando", "mensagem": MENSAGENS["acordando"], "fim_em": iso_utc(_sync["fim"])}
    if _sync["ok"] is None:
        return {"estado": "acordando", "mensagem": MENSAGENS["acordando"], "fim_em": None}
    if _sync["ok"]:
        return {"estado": "ok", "mensagem": "Sensores conectados.", "fim_em": iso_utc(_sync["fim"]), "executando": _sync["executando"]}
    tipo = _sync["tipo_erro"] or "erro"
    return {"estado": tipo, "mensagem": MENSAGENS[tipo], "fim_em": iso_utc(_sync["fim"]), "executando": _sync["executando"]}


def _registro_api(reg):
    """Valida UM registro da API. Retorna (id, codigo, quando_utc, valores) ou None se estiver quebrado ou fora da faixa
    (por exemplo, o teste com 100 °C)."""
    try:
        id_, codigo = int(reg["id"]), str(reg["codigo_esp32"]).strip().upper()
        quando = datetime.fromisoformat(str(reg["data_hora"]).replace("Z", "+00:00"))
        if quando.tzinfo is not None:   # a API manda em UTC, com o fuso explícito (+00:00)
            quando = quando.astimezone(timezone.utc).replace(tzinfo=None)
        valores = {}
        for campo, (mn, mx) in FAIXAS_LEITURA.items():
            v = reg.get(campo)
            if v is None:
                continue
            if isinstance(v, bool):
                return None
            v = float(v)
            if not mn <= v <= mx:
                return None
            valores[campo] = v
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    if not valores or not CODIGO_RE.match(codigo) or quando > agora_utc() + timedelta(minutes=10):
        return None
    return id_, codigo, quando, valores


LIMITE_BUSCA = 5000
CONFERE_A_CADA_S = 600   # de tempos em tempos, busca tudo para tirar da lista o que sumiu da API
_ultima_completa = [0.0]


def sincronizar_sensores(completa=False):
    """Busca na API as leituras novas e as guarda. Todo código que a API devolve vira um sensor (sem lugar, até alguém
    colocá-lo no mapa). Pede só o que é novo (?desde_id=); se a API ainda ignora o filtro, devolve tudo e pulamos o que já temos.
    Numa busca `completa` (sem filtro) também apaga os sensores sem lugar que a API não conhece mais."""
    desde = db.session.scalar(select(func.max(Leitura.externo_id))) or 0
    completa = completa or time.time() - _ultima_completa[0] > CONFERE_A_CADA_S
    pedido = {"ordem": "asc", "limite": LIMITE_BUSCA}
    if desde and not completa:
        pedido["desde_id"] = desde
    r = requests.get(f"{SENSORES_API}/dados", params=pedido, timeout=(6, 50),
                     headers={"X-API-Key": SENSORES_API_CHAVE} if SENSORES_API_CHAVE else None)
    r.raise_for_status()
    dados = r.json()
    if not isinstance(dados, list):
        raise ValueError("a API não devolveu uma lista")

    por_codigo = {s.codigo: s for s in db.session.scalars(select(Sensor).where(Sensor.exemplo.is_(False)))}
    ja_tem = set(db.session.execute(select(Leitura.sensor_id, Leitura.externo_id).where(Leitura.externo_id > desde)).all())
    novas = 0
    for reg in sorted((x for x in dados if isinstance(x, dict)), key=lambda x: x.get("id") if isinstance(x.get("id"), int) else 0):
        ok = _registro_api(reg)
        if not ok:
            continue
        id_, codigo, quando, valores = ok
        if id_ <= desde:
            continue   # já importada antes (a API atual ignora ?desde_id= e devolve tudo)
        sensor = por_codigo.get(codigo)
        if sensor is None:
            sensor = por_codigo[codigo] = Sensor(codigo=codigo)
            db.session.add(sensor)
            db.session.flush()
        if (sensor.id, id_) in ja_tem:
            continue
        ja_tem.add((sensor.id, id_))
        db.session.add(Leitura(sensor_id=sensor.id, externo_id=id_, recebido_em=quando, **valores))
        novas += 1
        if novas >= 5000:   # trava de segurança numa primeira busca gigante; o resto entra na próxima
            break
    if completa and len(dados) < LIMITE_BUSCA:   # lista inteira: dá para saber o que a API não tem mais
        _tirar_sumidos({str(x.get("codigo_esp32", "")).strip().upper() for x in dados if isinstance(x, dict)})
        _ultima_completa[0] = time.time()
    db.session.commit()
    return novas


def _tirar_sumidos(codigos_da_api):
    """Sensor sem lugar que a API não devolve mais (alguém apagou no banco dela) sai da lista, com as leituras dele.
    Sensor já colocado no mapa fica: a turma cadastrou, e pode estar só esperando a primeira leitura."""
    for s in db.session.scalars(select(Sensor).where(Sensor.exemplo.is_(False), Sensor.propriedade_id.is_(None))):
        if s.codigo not in codigos_da_api:
            db.session.delete(s)


def _rodar_sincronizacao(completa=False):
    with app.app_context():
        ok, tipo, novas = True, None, 0
        try:
            novas = sincronizar_sensores(completa)
            renovar_leituras()   # mantém os exemplos "funcionando"
        except Exception as e:
            db.session.rollback()
            ok, tipo = False, classificar_erro(e)
            app.logger.warning("Busca dos sensores falhou: %r", e)
        finally:
            db.session.remove()
        _sync.update(ok=ok, tipo_erro=tipo, novas=novas, fim=agora_utc(), executando=False)


def iniciar_sincronizacao(forcar=False):
    """Dispara a busca em segundo plano (a API pode demorar 20 s para acordar e ninguém fica esperando).
    Sem `forcar`, respeita o intervalo. Retorna True se começou uma busca."""
    if not SENSORES_API:
        return False
    with _trava_sync:
        if _sync["executando"] or (not forcar and time.time() - _sync["inicio"] < SENSORES_SYNC_S):
            return False
        _sync.update(executando=True, inicio=time.time())
    threading.Thread(target=_rodar_sincronizacao, args=(forcar,), daemon=True, name="sensores").start()
    return True


@app.post("/api/sincronizar")
def api_sincronizar():
    """Botão "Buscar agora". No máximo uma busca a cada 5 s, para ninguém sobrecarregar a API."""
    if time.time() - _sync["inicio"] < 5:
        return jsonify({"iniciada": False})
    return jsonify({"iniciada": iniciar_sincronizacao(forcar=True)})


def _laco_sincronizacao():
    while True:
        try:
            iniciar_sincronizacao()
        except Exception:
            app.logger.exception("Falha ao iniciar a busca dos sensores")
        time.sleep(3)


def iniciar_segundo_plano():
    """Liga a busca automática. Chamado pelo iniciar.py (e pelo modo de desenvolvimento abaixo)."""
    threading.Thread(target=_laco_sincronizacao, daemon=True, name="laco-sensores").start()


if __name__ == "__main__":
    # Modo de desenvolvimento: python app.py (o programa de verdade é aberto pelo iniciar.py)
    iniciar_segundo_plano()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
