(() => {
  const CHAVE = 'npc-decisoes';
  const CHAVE_VISTOS = 'npc-novos-vistos';
  const DIAS_NOVO = 7;
  const renderBase = render;

  function lerDecisoesCompletas() {
    try {
      const bruto = JSON.parse(localStorage.getItem(CHAVE) || '{}');
      if (!bruto || typeof bruto !== 'object' || Array.isArray(bruto)) return {};
      return Object.fromEntries(Object.entries(bruto).filter(([, v]) => ['favorito','descartado','indisponivel'].includes(v)));
    } catch { return {}; }
  }

  function lerVistos() {
    try {
      const bruto = JSON.parse(localStorage.getItem(CHAVE_VISTOS) || '[]');
      return new Set(Array.isArray(bruto) ? bruto.filter(Boolean) : []);
    } catch { return new Set(); }
  }

  const vistosNovos = lerVistos();
  state.decisoes = lerDecisoesCompletas();

  salvarDecisoes = function salvarDecisoesUX() {
    try { localStorage.setItem(CHAVE, JSON.stringify(state.decisoes)); } catch {}
  };
  function salvarVistos() {
    try { localStorage.setItem(CHAVE_VISTOS, JSON.stringify([...vistosNovos])); } catch {}
  }

  function dataValida(v) {
    if (!v) return null;
    const d = new Date(String(v).includes('T') ? v : `${v}T12:00:00`);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  function novoPorData(item) {
    const d = dataValida(item.primeiroVistoEm);
    if (!d || !ativo(item) || vistosNovos.has(item.id)) return false;
    const idade = (Date.now() - d.getTime()) / 86400000;
    return idade >= 0 && idade <= DIAS_NOVO;
  }

  ehNovo = novoPorData;
  inicializarNovos = function inicializarNovosUX(items) {
    state.novosIds = new Set(items.filter(novoPorData).map(i => i.id).filter(Boolean));
    state.baselineNovosInicializado = true;
  };
  marcarNovosComoVistos = function marcarNovosComoVistosUX() {
    state.novosIds.forEach(id => vistosNovos.add(id));
    salvarVistos();
    state.novosIds = new Set();
    render();
  };

  function indisponivelLocal(item) { return decisao(item.id) === 'indisponivel'; }
  function descartadoLocal(item) { return decisao(item.id) === 'descartado'; }
  function disponivelParaSugestao(item) {
    return ativo(item)
      && item.elegibilidade?.elegivel === true
      && !indisponivelLocal(item)
      && !descartadoLocal(item)
      && !foraDosCriterios(item);
  }

  distanciaHospital = function distanciaHospitalUX(item) {
    const hospital = item.hospital || {};
    if (hospital.localizacaoValidada !== true) return null;
    const km = hospital.distanciaKm ?? hospital.distanciaLinhaRetaKm;
    if (km == null || !Number.isFinite(Number(km))) return null;
    const distancia = Number(km).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
    return `${distancia} km do hospital${hospital.precisaoLocalizacao === 'bairro' ? ' aprox.' : ''}`;
  };

  origemTexto = function origemTextoUX(item) {
    const modo = item.proveniencia?.modo || item.fonteVerificacao;
    if (modo === 'coleta_automatica' || item.coletaAutomaticaPermitida === true) return 'Fonte monitorada';
    if (item.url) return 'Anúncio verificado';
    return null;
  };

  filtrar = function filtrarUX(items) {
    const somenteElegiveis = document.querySelector('#somenteElegiveis')?.checked;
    let rows = items;
    if (somenteElegiveis && !['a-confirmar','descartados'].includes(state.tab)) {
      rows = rows.filter(i => i.elegibilidade?.elegivel === true);
    }
    rows = rows.filter(i => {
      const d = decisao(i.id);
      if (state.tab === 'favoritados') return d === 'favorito' && ativo(i);
      if (state.tab === 'descartados') return d === 'descartado' || d === 'indisponivel';
      if (state.tab === 'a-confirmar') return !['descartado','indisponivel'].includes(d) && precisaConfirmacao(i) && ativo(i);
      if (state.tab === 'novos') return !['descartado','indisponivel'].includes(d) && state.novosIds.has(i.id) && ativo(i);
      if (state.tab === 'todos') return disponivelParaSugestao(i);
      return true;
    });
    const ordem = document.querySelector('#ordenacao')?.value || 'recente';
    return rows.sort((a,b) => {
      const prioridade = prioridadeCandidato(a) - prioridadeCandidato(b);
      if (prioridade !== 0) return prioridade;
      if (ordem === 'preco') return (a.aluguel ?? Infinity) - (b.aluguel ?? Infinity);
      if (ordem === 'recente') {
        const novo = Number(novoPorData(b)) - Number(novoPorData(a));
        if (novo !== 0) return novo;
        const data = String(b.primeiroVistoEm || '').localeCompare(String(a.primeiroVistoEm || ''));
        if (data !== 0) return data;
      }
      return (b.match?.final ?? -1) - (a.match?.final ?? -1);
    });
  };

  function normalizarNome(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }
  function itemPertenceFonte(item, fonte) {
    const origem = normalizarNome(item?.fonte);
    return [fonte?.nome, ...(Array.isArray(fonte?.aliases) ? fonte.aliases : [])].map(normalizarNome).filter(Boolean).some(nome => origem.includes(nome));
  }
  function coberturaFonte(fonte) {
    const relacionados = state.imoveis.filter(item => itemPertenceFonte(item, fonte));
    const ativos = relacionados.filter(item => typeof candidatoAtivo === 'function' ? candidatoAtivo(item) : ativo(item));
    return {
      ativos: ativos.length,
      minimos: ativos.filter(item => item.elegibilidade?.elegivel === true).length,
      comFoto: ativos.filter(item => fotosConfiaveis(item).length > 0).length
    };
  }

  renderImobiliarias = function renderImobiliariasUX() {
    const lista = document.querySelector('#lista');
    lista.className = 'lista-fontes';
    const imobiliarias = state.fontes.filter(f => f.tipo === 'imobiliaria');
    if (!imobiliarias.length) { lista.innerHTML = '<div class="vazio"><strong>Nenhuma imobiliária carregada.</strong></div>'; return; }
    const enriquecidas = imobiliarias.map(fonte => ({ fonte, cobertura: coberturaFonte(fonte) }));
    enriquecidas.sort((a,b) => b.cobertura.ativos - a.cobertura.ativos || a.fonte.nome.localeCompare(b.fonte.nome, 'pt-BR'));
    lista.innerHTML = `<div class="fontes-intro"><strong>${imobiliarias.length} imobiliárias no radar</strong><span>Acesso direto às fontes.</span></div>` + enriquecidas.map(({ fonte, cobertura }) => {
      const link = fonte.siteUrl ? `<a href="${fonte.siteUrl}" target="_blank" rel="noopener noreferrer">Abrir site</a>` : '<span class="sem-link">Site em verificação</span>';
      const info = cobertura.ativos ? `${cobertura.ativos} candidato${cobertura.ativos === 1 ? '' : 's'}${cobertura.comFoto ? ` · ${cobertura.comFoto} com foto` : ''}` : 'Sem candidato ativo';
      return `<article class="fonte-card"><div><strong>${fonte.nome}</strong></div><p class="fonte-cobertura">${info}</p>${link}</article>`;
    }).join('');
  };

  function limparTextoTecnico(card, item) {
    const alertas = [...card.querySelectorAll('.alertas span')];
    alertas.forEach(el => {
      const texto = el.textContent.trim();
      if (/avaliação visual ainda não calculada/i.test(texto)) el.remove();
      else if (/sem foto real disponível/i.test(texto)) el.textContent = 'Sem foto';
      else if (/falta confirmar:/i.test(texto)) el.textContent = texto.replace(/^Falta confirmar:\s*/i, 'Confirmar: ');
    });
    const box = card.querySelector('.alertas');
    if (box && !box.children.length) box.hidden = true;
    if (item.elegibilidade?.elegivel === true) {
      card.classList.add('card-confirmado');
    }
  }

  function aplicarRotulos() {
    document.querySelectorAll('.qualidade[data-tipo="elegivel"]').forEach(el => { el.textContent = 'Mínimos OK'; el.title = 'Cumpre os critérios mínimos confirmados.'; });
    document.querySelectorAll('.match-pendente').forEach(el => { el.hidden = true; });
    document.querySelectorAll('.proveniencia').forEach(el => el.classList.add('proveniencia-secundaria'));
  }

  function aplicarVazio() {
    const vazio = document.querySelector('#lista .vazio');
    if (!vazio) return;
    const mensagens = {
      'todos': ['Sem sugestões confirmadas agora.', 'Veja “A confirmar” para anúncios que ainda precisam de informação.'],
      'novos': ['Nada novo por aqui.', 'Novos anúncios aparecem aqui por 7 dias.'],
      'a-confirmar': ['Nada pendente agora.', 'Ótimo: não há anúncios aguardando confirmação.'],
      'favoritados': ['Nenhum favorito ainda.', 'Salve as casas que vocês querem comparar.'],
      'descartados': ['Nada descartado.', 'Casas rejeitadas ou já alugadas ficam aqui.']
    };
    const [titulo, apoio] = mensagens[state.tab] || ['Nada por aqui.', ''];
    vazio.innerHTML = `<strong>${titulo}</strong>${apoio ? `<span>${apoio}</span>` : ''}`;
  }

  function aplicarDecisoesVisuais() {
    const cards = [...document.querySelectorAll('.card')];
    const visiveis = filtrar(state.imoveis.filter(ativo));
    cards.forEach((card, index) => {
      const item = visiveis[index];
      if (!item) return;
      limparTextoTecnico(card, item);
      const d = decisao(item.id);
      const indisponivel = card.querySelector('.indisponivel');
      if (!indisponivel) return;
      const estado = card.querySelector('.estado-anuncio');
      const fav = card.querySelector('.favoritar');
      const descartar = card.querySelector('.descartar');

      if (d === 'indisponivel') {
        card.classList.add('indisponivel-card');
        indisponivel.textContent = '↩ Restaurar';
        if (estado) { estado.hidden = false; estado.textContent = 'Alugado / indisponível'; }
      } else {
        indisponivel.textContent = '⌂ Alugado';
        if (estado) estado.hidden = true;
      }
      indisponivel.onclick = () => setDecisaoUX(item.id, d === 'indisponivel' ? null : 'indisponivel');

      if (fav) {
        fav.textContent = d === 'favorito' ? '♥ Salvo' : '♡ Salvar';
      }
      if (descartar && d !== 'indisponivel') {
        descartar.textContent = d === 'descartado' ? '↩ Restaurar' : '✕ Não quero';
      }
    });
  }

  function setDecisaoUX(id, valor) {
    if (valor === null || decisao(id) === valor) delete state.decisoes[id];
    else state.decisoes[id] = valor;
    salvarDecisoes();
    render();
  }
  setDecisao = setDecisaoUX;

  const renderResumoBase = renderResumo;
  renderResumo = function renderResumoUX() {
    renderResumoBase();
    const ativos = state.imoveis.filter(ativo);
    const sugestoes = ativos.filter(disponivelParaSugestao).length;
    const favoritos = ativos.filter(i => decisao(i.id) === 'favorito').length;
    const descartados = state.imoveis.filter(i => ['descartado','indisponivel'].includes(decisao(i.id))).length;
    const confirmar = ativos.filter(i => precisaConfirmacao(i) && !['descartado','indisponivel'].includes(decisao(i.id))).length;
    const novos = ativos.filter(i => state.novosIds.has(i.id) && !['descartado','indisponivel'].includes(decisao(i.id))).length;
    document.querySelector('#resumo').innerHTML = [metric('sugestões', sugestoes), metric('novos', novos), metric('a confirmar', confirmar), metric('favoritos', favoritos)].join('');
    const set = (tab, texto, n) => { const el = document.querySelector(`[data-tab="${tab}"]`); if (el) el.textContent = n ? `${texto} (${n})` : texto; };
    set('todos','Sugestões',sugestoes); set('novos','Novos',novos); set('a-confirmar','A confirmar',confirmar); set('favoritados','Favoritos',favoritos); set('descartados','Descartados',descartados);
  };

  render = function renderUX() {
    renderBase();
    aplicarRotulos();
    aplicarVazio();
    aplicarDecisoesVisuais();
  };

  textoStatus = function textoStatusUX(inv, status, fontesData) {
    const atualizado = dataPtBr(inv.atualizadoEm || status?.fim);
    const imobiliarias = (fontesData?.fontes || []).filter(f => f.tipo === 'imobiliaria').length;
    return [atualizado ? `Atualizado ${atualizado}` : null, imobiliarias ? `${imobiliarias} fontes` : null].filter(Boolean).join(' · ') || 'Radar atualizado';
  };

  function codificarEscolhas() {
    const payload = JSON.stringify({ v:2, decisoes: state.decisoes, vistos:[...vistosNovos] });
    return btoa(unescape(encodeURIComponent(payload))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  }
  function decodificarEscolhas(token) {
    try {
      const base = token.replace(/-/g,'+').replace(/_/g,'/');
      const pad = base + '='.repeat((4 - base.length % 4) % 4);
      const payload = JSON.parse(decodeURIComponent(escape(atob(pad))));
      if (![1,2].includes(payload?.v) || !payload.decisoes || typeof payload.decisoes !== 'object') return null;
      return payload;
    } catch { return null; }
  }
  function importarDaUrl() {
    const params = new URLSearchParams(location.search);
    const compartilhadas = decodificarEscolhas(params.get('escolhas') || '');
    if (!compartilhadas) return;
    Object.entries(compartilhadas.decisoes).forEach(([id, valor]) => { if (['favorito','descartado','indisponivel'].includes(valor)) state.decisoes[id] = valor; });
    if (Array.isArray(compartilhadas.vistos)) compartilhadas.vistos.forEach(id => { if (id) vistosNovos.add(id); });
    salvarDecisoes();
    salvarVistos();
    params.delete('escolhas');
    const query = params.toString();
    history.replaceState(null,'',`${location.pathname}${query ? `?${query}` : ''}${location.hash}`);
    const feedback = document.querySelector('#syncFeedback');
    if (feedback) feedback.textContent = 'Celular sincronizado';
  }
  async function compartilharEscolhas() {
    const url = `${location.origin}${location.pathname}?escolhas=${codificarEscolhas()}`;
    const feedback = document.querySelector('#syncFeedback');
    try {
      if (navigator.share) await navigator.share({ title:'Nossa Próxima Casa', text:'Abra este link no outro celular para sincronizar as escolhas.', url });
      else if (navigator.clipboard) { await navigator.clipboard.writeText(url); if (feedback) feedback.textContent = 'Link copiado'; }
      else { prompt('Copie este link', url); }
    } catch (e) { if (e?.name !== 'AbortError' && feedback) feedback.textContent = 'Não foi possível compartilhar'; }
  }

  state.tab = 'todos';
  const somente = document.querySelector('#somenteElegiveis');
  if (somente) somente.checked = false;
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('ativo', b.dataset.tab === 'todos'));
  document.querySelector('#compartilharEscolhas')?.addEventListener('click', compartilharEscolhas);
  importarDaUrl();
})();
