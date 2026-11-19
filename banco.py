"""
Banco de dados do EcoGuard (SQLite local, via SQLAlchemy).

Tabelas
  propriedades   lugares marcados no mapa: um PONTO (lat, lon) + um RAIO em metros
  sensores       ESP32 (e os sensores de exemplo). Sem propriedade = "sensor sem lugar"
  leituras       medições de cada sensor

Datas ficam como DateTime "ingênuo" em UTC (agora_utc).
O arquivo do banco fica em %APPDATA%\\EcoGuard (nunca ao lado do programa).
"""
import os
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, event, func, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def pasta_dados():
    """Pasta onde o EcoGuard guarda o banco: %APPDATA%\\EcoGuard no Windows (ECOGUARD_DADOS troca, para testes)."""
    base = os.environ.get("ECOGUARD_DADOS")
    if not base:
        raiz = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
        base = os.path.join(raiz, "EcoGuard")
    os.makedirs(base, exist_ok=True)
    return base


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def agora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


AGORA_SQL = text("(datetime('now'))")


def _data_agora():
    return mapped_column(DateTime, default=agora_utc, server_default=AGORA_SQL)


class Propriedade(db.Model):
    __tablename__ = "propriedades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    raio_m: Mapped[float] = mapped_column(Float)
    exemplo: Mapped[bool] = mapped_column(default=False, server_default=text("0"))   # veio pronta com o programa
    criado_em: Mapped[datetime] = _data_agora()

    sensores: Mapped[list["Sensor"]] = relationship(back_populates="propriedade")


class Sensor(db.Model):
    __tablename__ = "sensores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    propriedade_id: Mapped[int | None] = mapped_column(ForeignKey("propriedades.id", ondelete="SET NULL"))
    codigo: Mapped[str] = mapped_column(String, unique=True)     # ESP32_001... (exemplos: EXEMPLO-01)
    nome: Mapped[str | None] = mapped_column(String)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    exemplo: Mapped[bool] = mapped_column(default=False, server_default=text("0"))   # sensor de mentira, só local
    criado_em: Mapped[datetime] = _data_agora()

    propriedade: Mapped["Propriedade | None"] = relationship(back_populates="sensores")
    leituras: Mapped[list["Leitura"]] = relationship(back_populates="sensor", cascade="all, delete-orphan",
                                                     passive_deletes=True)


class Leitura(db.Model):
    __tablename__ = "leituras"
    __table_args__ = (Index("idx_leituras_sensor", "sensor_id", "recebido_em"),
                      Index("idx_leituras_externo", "sensor_id", "externo_id", unique=True))   # não importa a mesma leitura duas vezes

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensores.id", ondelete="CASCADE"))
    umidade_ar: Mapped[float | None] = mapped_column(Float)
    umidade_solo: Mapped[float | None] = mapped_column(Float)
    temperatura: Mapped[float | None] = mapped_column(Float)
    recebido_em: Mapped[datetime] = _data_agora()                 # UTC
    externo_id: Mapped[int | None] = mapped_column(Integer)       # id da leitura na API dos sensores (vazio nos exemplos)

    sensor: Mapped["Sensor"] = relationship(back_populates="leituras")


def _ativar_chaves_estrangeiras(conexao, _registro):
    conexao.execute("PRAGMA foreign_keys = ON")   # sem isso o SQLite ignora ON DELETE


def init_db(app):
    caminho = os.environ.get("ECOGUARD_DB") or os.path.join(pasta_dados(), "ecoguard.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.abspath(caminho).replace("\\", "/")
    db.init_app(app)
    with app.app_context():
        event.listen(db.engine, "connect", _ativar_chaves_estrangeiras)
        db.create_all()


def ultimas_leituras(ids=None):
    """Última leitura de cada sensor, numa consulta só: {sensor_id: Leitura}. ids=None considera todos."""
    ordem = (Leitura.recebido_em.desc(), Leitura.id.desc())
    posicao = func.row_number().over(partition_by=Leitura.sensor_id, order_by=ordem).label("posicao")
    q = select(Leitura.id.label("id"), posicao)
    if ids is not None:
        if not ids:
            return {}
        q = q.where(Leitura.sensor_id.in_(ids))
    sub = q.subquery()
    linhas = db.session.scalars(select(Leitura).join(sub, Leitura.id == sub.c.id).where(sub.c.posicao == 1))
    return {l.sensor_id: l for l in linhas}
