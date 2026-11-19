"""
Abre o EcoGuard como um programa de verdade: sobe o servidor numa porta livre, abre uma janela própria
(pywebview) e encerra tudo quando a janela fecha. Sem terminal. Se a janela não puder abrir
(falta o WebView2, por exemplo), abre no navegador padrão.
"""
import os
import socket
import sys
import threading
import time
import webbrowser

# Sem console (--noconsole) o Python não tem stdout/stderr, e isso quebra o log do Flask: manda para um arquivo.
if sys.stdout is None or sys.stderr is None:
    from banco import pasta_dados
    _log = open(os.path.join(pasta_dados(), "ecoguard.log"), "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or _log
    sys.stderr = sys.stderr or _log

from werkzeug.serving import make_server

import app as ecoguard


def porta_livre():
    """Pede ao Windows uma porta que ninguém está usando (a 5000 pode estar ocupada)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    porta = int(os.environ.get("ECOGUARD_PORTA") or porta_livre())
    servidor = make_server("127.0.0.1", porta, ecoguard.app, threaded=True)
    threading.Thread(target=servidor.serve_forever, daemon=True, name="servidor").start()
    ecoguard.iniciar_segundo_plano()
    url = f"http://127.0.0.1:{porta}/"

    try:
        import webview
        webview.create_window("EcoGuard", url, width=1366, height=820, min_size=(900, 600), maximized=True)
        webview.start()   # só volta quando a janela fecha
    except Exception as e:
        print("Janela própria indisponível, abrindo no navegador:", repr(e))
        webbrowser.open(url)
        try:
            while True:   # o programa continua até alguém fechar este processo
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    servidor.shutdown()
    os._exit(0)   # encerra já, sem esperar as threads de segundo plano


if __name__ == "__main__":
    main()
