"""
Dados de exemplo do EcoGuard: 5 propriedades e 10 sensores espalhados pelo Brasil.

Tudo isso é LOCAL e de mentira (marcado como "exemplo" na tela). Nada daqui vai para a API dos sensores.
"""
import random
from datetime import timedelta

from sqlalchemy import delete, select

from banco import Leitura, Propriedade, Sensor, agora_utc, db

# nome, lat, lon, raio (m), sensores: (nome, deslocamento lat, lon, temp, umidade do ar, umidade do solo, situação)
# situação: "ok" envia agora · "parado" parou há 3 horas · "novo" ainda não enviou nada
PROPRIEDADES = [
    ("Sítio Mata Verde", -19.885, -44.425, 450, [
        ("Sensor da horta", 0.002, -0.001, 27.5, 58, 46, "ok"),
        ("Sensor do pomar", -0.002, 0.002, 29.0, 52, 38, "ok")]),
    ("Reserva Serra Azul", -19.270, -43.560, 900, [
        ("Sensor da trilha", 0.003, 0.002, 24.0, 71, 62, "ok"),
        ("Sensor da nascente", -0.003, -0.002, 22.5, 82, 78, "parado")]),
    ("Horta da Escola", -20.755, -42.875, 150, [
        ("Sensor dos canteiros", 0.0005, 0.0005, 30.5, 45, 33, "ok"),
        ("Sensor da estufa", -0.0006, -0.0004, 33.0, 60, 55, "novo")]),
    ("Chácara Cerrado Vivo", -15.795, -47.890, 600, [
        ("Sensor do pasto", 0.002, 0.003, 34.5, 28, 18, "ok"),
        ("Sensor da mata", -0.002, -0.002, 31.0, 36, 27, "ok")]),
    ("Fazenda Rio Claro", -21.130, -56.480, 1200, [
        ("Sensor da lagoa", 0.004, 0.003, 32.0, 66, 70, "ok"),
        ("Sensor do curral", -0.004, -0.003, 33.5, 55, 40, "ok")]),
]


# EXEMPLO-01, EXEMPLO-02... na ordem da lista acima -> (situação, valores-base)
SITUACAO = {}
for _p in PROPRIEDADES:
    for _s in _p[4]:
        SITUACAO[f"EXEMPLO-{len(SITUACAO) + 1:02d}"] = (_s[6], _s[3:6])


def _leitura(base, jitter):
    t, ar, solo = base
    return dict(temperatura=round(t + random.uniform(-jitter, jitter), 1),
                umidade_ar=round(min(100, max(5, ar + random.uniform(-3 * jitter, 3 * jitter))), 1),
                umidade_solo=round(min(100, max(5, solo + random.uniform(-2 * jitter, 2 * jitter))), 1))


def renovar_leituras():
    """Dá uma leitura nova aos sensores de exemplo que "enviam" (para continuarem como Funcionando) e apaga as antigas."""
    agora = agora_utc()
    ok = {}
    for s in db.session.scalars(select(Sensor).where(Sensor.exemplo.is_(True))):
        situacao, base = SITUACAO.get(s.codigo, (None, None))
        if situacao == "ok":
            ok[s.id] = base
            db.session.add(Leitura(sensor_id=s.id, recebido_em=agora, **_leitura(base, 1.2)))
    if ok:
        db.session.execute(delete(Leitura).where(Leitura.recebido_em < agora - timedelta(hours=6), Leitura.sensor_id.in_(list(ok))))
    db.session.commit()


def restaurar_exemplos():
    """Apaga os exemplos e cria de novo. O que a turma cadastrou (propriedades e sensores próprios) não é tocado."""
    for p in db.session.scalars(select(Propriedade).where(Propriedade.exemplo.is_(True))):
        db.session.delete(p)
    db.session.execute(delete(Sensor).where(Sensor.exemplo.is_(True)))
    db.session.flush()
    agora = agora_utc()
    n = 0
    for nome, lat, lon, raio, sensores in PROPRIEDADES:
        p = Propriedade(nome=nome, lat=lat, lon=lon, raio_m=raio, exemplo=True)
        db.session.add(p)
        db.session.flush()
        for sn, dlat, dlon, t, ar, solo, situacao in sensores:
            n += 1
            codigo = f"EXEMPLO-{n:02d}"
            s = Sensor(propriedade_id=p.id, codigo=codigo, nome=sn, lat=lat + dlat, lon=lon + dlon, exemplo=True)
            db.session.add(s)
            db.session.flush()
            if situacao == "ok":
                for minutos in (50, 25, 0):   # um pequeno histórico
                    db.session.add(Leitura(sensor_id=s.id, recebido_em=agora - timedelta(minutes=minutos), **_leitura((t, ar, solo), 1.5)))
            elif situacao == "parado":
                db.session.add(Leitura(sensor_id=s.id, recebido_em=agora - timedelta(hours=3), **_leitura((t, ar, solo), 1)))
    db.session.commit()


def garantir_exemplos():
    """Na primeira vez que o programa abre (banco vazio), cria os exemplos. Nas outras, só renova as leituras."""
    if db.session.scalar(select(Propriedade.id).limit(1)) is None and db.session.scalar(select(Sensor.id).limit(1)) is None:
        restaurar_exemplos()
    else:
        renovar_leituras()
