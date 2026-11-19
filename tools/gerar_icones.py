"""Gera os ícones do EcoGuard a partir de static/img/logo-original.jpg (rode: python tools/gerar_icones.py)."""
import os
from collections import deque
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(RAIZ, "static", "img")
orig = Image.open(os.path.join(IMG, "logo-original.jpg")).convert("RGB")


def sem_fundo(im, tol=18):
    """Deixa transparente o fundo claro ligado às bordas (não mexe no branco do robô)."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    claro = lambda p: min(p[:3]) >= 255 - tol
    visto = bytearray(w * h)
    fila = deque([(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)])
    while fila:
        x, y = fila.popleft()
        if not (0 <= x < w and 0 <= y < h) or visto[y * w + x] or not claro(px[x, y]):
            continue
        visto[y * w + x] = 1
        px[x, y] = (255, 255, 255, 0)
        fila.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def quadrado(im, lado, fundo=None, margem=0.08):
    """Centraliza a imagem num quadrado lado x lado (fundo=None: transparente)."""
    saida = Image.new("RGBA", (lado, lado), fundo or (0, 0, 0, 0))
    area = int(lado * (1 - 2 * margem))
    c = im.copy(); c.thumbnail((area, area), Image.LANCZOS)
    saida.paste(c, ((lado - c.width) // 2, (lado - c.height) // 2), c)
    return saida


# Logo completo, sem fundo (cabeçalho e tela inicial)
logo = sem_fundo(orig)
logo.save(os.path.join(IMG, "logo.png"), optimize=True)
# Só a cabeça do robô (cabeçalho pequeno)
robo = sem_fundo(orig.crop((340, 208, 880, 590)), 22)
robo.save(os.path.join(IMG, "mascote.png"), optimize=True)

NAVY = (6, 30, 56, 255)
for nome, lado in (("icone-180.png", 180), ("icone-192.png", 192), ("icone-512.png", 512)):
    quadrado(logo, lado, (255, 255, 255, 255), 0.03).convert("RGB").save(os.path.join(IMG, nome), optimize=True)
quadrado(logo, 512, (255, 255, 255, 255), 0.14).convert("RGB").save(os.path.join(IMG, "icone-maskable-512.png"), optimize=True)
quadrado(logo, 256, (255, 255, 255, 255), 0.02).save(os.path.join(IMG, "ecoguard.ico"),
                                     sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
quadrado(logo, 64, None, 0.0).save(os.path.join(IMG, "favicon.png"), optimize=True)
print("ok")
