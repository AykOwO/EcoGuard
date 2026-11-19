// Funções compartilhadas entre as telas do EcoGuard
const EcoGuard = {
  // ---------------------------------------------------------------- servidor
  async api(url, opts = {}) {
    const headers = { "X-EcoGuard": "1", ...(opts.headers || {}) };
    let body = opts.body;
    if (body && typeof body !== "string") body = JSON.stringify(body);
    if (body) headers["Content-Type"] = "application/json";
    let r;
    try {
      r = await fetch(url, { ...opts, headers, body });
    } catch {
      throw new Error("Não consegui falar com o programa. Feche o EcoGuard e abra de novo.");
    }
    const dados = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(dados.erro || `Algo deu errado (erro ${r.status}).`);
    return dados;
  },

  // ---------------------------------------------------------------- texto
  esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); },
  num(v, casas = 1) { return Number(v).toLocaleString("pt-BR", { maximumFractionDigits: casas }); },
  distancia(m) { return m < 1000 ? `${Math.round(m)} m` : `${EcoGuard.num(m / 1000, m < 10000 ? 1 : 0)} km`; },
  haQuanto(isoUtc) {
    const min = Math.round((Date.now() - new Date(isoUtc).getTime()) / 60000);
    if (min < 1) return "agora mesmo";
    if (min < 60) return `há ${min} min`;
    if (min < 1440) return `há ${Math.round(min / 60)} h`;
    return `há ${Math.round(min / 1440)} dias`;
  },
  ESTADO: { funcionando: "Funcionando", sem_sinal: "Sem sinal", esperando: "Esperando" },
  chipEstado(e) { return `<span class="chip ${e}">${EcoGuard.ESTADO[e]}</span>`; },

  toast(msg, ms = 4000) {
    document.querySelectorAll(".toast").forEach(t => t.remove());
    const t = document.createElement("div");
    t.className = "toast"; t.setAttribute("role", "status"); t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), ms);
  },

  // ---------------------------------------------------------------- mapa
  CENTRO_PADRAO: [-19.88, -44.43],

  // Satélite da Esri + nomes dos lugares. Por baixo vai um mapa simples (quadriculado verde), que aparece sozinho
  // quando não há internet: o app nunca fica com a tela em branco.
  mapaBase(el, opts = {}) {
    const mapa = L.map(el, { zoomControl: true, attributionControl: true, minZoom: 3, ...opts });
    mapa.attributionControl.setPrefix(false);
    mapa.zoomControl.setPosition("bottomleft");

    const Simples = L.GridLayer.extend({
      createTile(c) {
        const t = document.createElement("canvas"); t.width = t.height = 256;
        const g = t.getContext("2d");
        g.fillStyle = "#CFE6C4"; g.fillRect(0, 0, 256, 256);
        g.strokeStyle = "rgba(6,30,56,.18)"; g.lineWidth = 1;
        for (let i = 0; i <= 256; i += 64) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, 256); g.moveTo(0, i); g.lineTo(256, i); g.stroke(); }
        return t;
      },
    });
    new Simples({ zIndex: 0 }).addTo(mapa);

    let avisou = false;
    const aviso = () => { if (!avisou) { avisou = true; EcoGuard.toast("Sem internet: o mapa de satélite não carregou. Mostrando o mapa simples."); } };
    const esri = "https://server.arcgisonline.com/ArcGIS/rest/services/";
    L.tileLayer(esri + "World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 21, maxNativeZoom: 19, zIndex: 1, attribution: "Imagens: Esri, Maxar, Earthstar Geographics",
    }).on("tileerror", aviso).addTo(mapa);
    L.tileLayer(esri + "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 21, maxNativeZoom: 19, opacity: .9, zIndex: 2,
    }).addTo(mapa);
    return mapa;
  },

  circuloPropriedade(ll, raio, fraco = false) {
    return L.circle(ll, { radius: raio, color: "#8AD321", weight: fraco ? 2 : 4, dashArray: "10 8", fillColor: "#8AD321", fillOpacity: fraco ? .06 : .16, interactive: false });
  },
  pinoLocal() {
    return L.divIcon({ className: "", iconSize: [40, 48], iconAnchor: [20, 46], html:
      '<svg viewBox="0 0 40 48" width="40" height="48" aria-hidden="true"><path d="M20 47C20 47 3 29.5 3 18.5a17 17 0 0 1 34 0C37 29.5 20 47 20 47z" fill="#2FA84F" stroke="#fff" stroke-width="2.5"/>' +
      '<path d="M26 12c-7 0-11 3.6-11 9 0 1.6.5 3 1.3 4 .8-3.4 3.4-6.2 7.4-7.6-3 2.4-4.8 5.3-5.4 8.7 1.1.5 2.2.8 3.4.8 4.2 0 6.8-3.5 6.8-8.4 0-2.2-.8-4.8-2.5-6.5z" fill="#fff"/></svg>' });
  },

  // Busca de lugar, com espera entre as teclas (o serviço aceita 1 pedido por segundo)
  buscaEndereco(input, caixa, aoEscolher) {
    let t = null;
    const buscar = async () => {
      const q = input.value.trim();
      if (q.length < 3) { caixa.innerHTML = ""; caixa.hidden = true; return; }
      caixa.hidden = false; caixa.innerHTML = "<p>Procurando...</p>";
      try {
        const itens = await EcoGuard.api(`/api/local?q=${encodeURIComponent(q)}`);
        if (!itens.length) { caixa.innerHTML = "<p>Não achei. Tente o nome da cidade.</p>"; return; }
        caixa.innerHTML = "";
        itens.forEach(i => {
          const b = document.createElement("button");
          b.type = "button"; b.textContent = i.nome;
          b.onclick = () => { caixa.hidden = true; input.blur(); aoEscolher(i); };
          caixa.appendChild(b);
        });
      } catch (e) { caixa.innerHTML = `<p>${EcoGuard.esc(e.message)}</p>`; }
    };
    input.addEventListener("input", () => { clearTimeout(t); t = setTimeout(buscar, 900); });
    input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); clearTimeout(t); buscar(); } });
  },
};
