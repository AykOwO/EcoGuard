# PyInstaller: pasta (--onedir), sem console. Gere com:  tools\gerar_exe.ps1
a = Analysis(
    ["iniciar.py"],
    pathex=["."],
    datas=[("templates", "templates"), ("static", "static")],
    hiddenimports=["sqlalchemy.dialects.sqlite"],
    excludes=["tkinter", "PIL"],   # Pillow só serve para gerar os ícones
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="EcoGuard", console=False,
          icon="static/img/ecoguard.ico", upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="EcoGuard", upx=False)
