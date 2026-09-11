function carregarDecisoes() {
  try {
    const bruto = JSON.parse(localStorage.getItem('npc-decisoes') || '{}');
    if (!bruto || typeof bruto !== 'object' || Array.isArray(bruto)) return {};
    return Object.fromEntries(Object.entries(bruto).filter(([, v]) => v === 'favorito' || v === 'descartado'));
  } catch {
    return {};
  }
}

const state = {
  tab: 'novos',
  imoveis: [],
  fontes: [],
  decisoes: carregarDecisoes(),
  novosIds: new Set(),
  baselineNovosInicializado: false
};
const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function salvarDecisoes() {
  try { localStorage.setItem('npc-decisoes', JSON.stringify(state.decisoes)); } catch {}
}
function decisao(id) { return state.decisoes[id] || null; }
function setDecisao(id, valor) {
  if (valor === null || decisao(id) === valor) delete state.decisoes[id];
  else state.decisoes[id] = valor;
  salvarDecisoes();
  render();
}
function valor(v, fallback = '—') { return v === null || v === undefined || v === '' ? fallback : v; }
function dataPtBr(v) {
  if (!v) return null;
  const d = new Date(String(v).includes('T') ? v : `${v}T12:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric' }).format(d);
}
function precisaConfirmacao(item) { return item.elegibilidade?.status === 'pendente'; }
function foraDosCriterios(item) { return item.elegibilidade?.status === 'inelegivel'; }
function ativo(item) { return item.disponivel !== false; }

function inicializarNovos(items) {
  const idsAtuais = items.filter(ativo).map(i => i.id).filter(Boolean);
  try {
    const raw = JSON.parse(localStorage.getItem('npc-inventario-conhecido') || 'null');
    if (!Array.isArray(raw)) {
      localStorage.setItem('npc-inventario-conhecido', JSON.stringify(idsAtuais));
      state.novosIds = new Set();
      state.baselineNovosInicializado = true;
      return;
    }
    const conhecidos = new Set(raw);
    state.novosIds = new Set(idsAtuais.filter(id => !conhecidos.has(id)));
  } catch {
    state.novosIds = new Set();
  }
  state.baselineNovosInicializado = true;
}
function ehNovo(item) { return Boolean(item?.id && state.novosIds.has(item.id)); }
function marcarNovosComoVistos() {
  try {
    const idsAtuais = state.imoveis.filter(ativo).map(i => i.id).filter(Boolean);
    localStorage.setItem('npc-inventario-conhecido', JSON.stringify(idsAtuais));
  } catch {}
  state.novosIds = new Set();
  render();
}

function prioridadeCandidato(item) {
  if (item.elegibilidade?.elegivel === true) return 0;
  if (precisaConfirmacao(item)) return 1;
  return 2;
}
function filtrar(items) {
  const somenteElegiveis = document.querySelector('#somenteElegiveis').checked;
  let rows = items.filter(i => !somenteElegiveis || i.elegibilidade?.elegivel === true);
  rows = rows.filter(i => {
    const d = decisao(i.id);
    if (state.tab === 'favoritados') return d === 'favorito';
    if (state.tab === 'descartados') return d === 'descartado';
    if (state.tab === 'a-confirmar') return d === null && precisaConfirmacao(i);
    if (state.tab === 'novos') return d === null && ehNovo(i);
    return true;
  });
  const ordem = document.querySelector('#ordenacao').value;
  return rows.sort((a,b) => {
    const prioridade = prioridadeCandidato(a) - prioridadeCandidato(b);
    if (prioridade !== 0) return prioridade;
    if (ordem === 'preco') return (a.aluguel ?? Infinity) - (b.aluguel ?? Infinity);
    if (ordem === 'recente') {
      const data = String(b.primeiroVistoEm || '').localeCompare(String(a.primeiroVistoEm || ''));
      return data !== 0 ? data : (b.match?.final ?? -1) - (a.match?.final ?? -1);
    }
    return (b.match?.final ?? -1) - (a.match?.final ?? -1);
  });
}

function metric(label, value, classe = '') { return `<div${classe ? ` class="${classe}"` : ''}><strong>${value}</strong><span>${label}</span></div>`; }
function renderResumo() {
  const ativos = state.imoveis.filter(ativo);
  const elegiveis = ativos.filter(i => i.elegibilidade?.elegivel === true).length;
  const confirmar = ativos.filter(i => precisaConfirmacao(i)).length;
  const fora = ativos.filter(i => foraDosCriterios(i)).length;
  document.querySelector('#resumo').innerHTML = [
    metric('anúncios acompanhados', ativos.length),
    metric('elegíveis confirmados', elegiveis),
    metric('a confirmar', confirmar),
    metric('fora dos critérios', fora)
  ].join('');
  const fav = ativos.filter(i => decisao(i.id) === 'favorito').length;
  document.querySelector('[data-tab="favoritados"]').textContent = fav ? `Favoritados (${fav})` : 'Favoritados';
  document.querySelector('[data-tab="novos"]').textContent = state.novosIds.size ? `Novos (${state.novosIds.size})` : 'Novos';
}

function distanciaHospital(item) {
  const hospital = item.hospital || {};
  if (hospital.localizacaoValidada !== true) return null;
  const km = hospital.distanciaKm ?? hospital.distanciaLinhaRetaKm;
  if (km == null || !Number.isFinite(Number(km))) return null;
  const aprox = hospital.precisaoLocalizacao === 'bairro' ? ' aprox.' : '';
  const tipo = hospital.distanciaKm != null ? '' : ' em linha reta';
  return `${Number(km).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} km${tipo}${aprox} do Hospital Santa Mônica`;
}
function fotosConfiaveis(item) {
  return [...new Set([
    item.fotoUrl, item.imagemUrl,
    ...(Array.isArray(item.fotos) ? item.fotos : []),
    ...(Array.isArray(item.imagens) ? item.imagens : [])
  ].filter(url => /^https:\/\//i.test(String(url))))];
}
function origemTexto(item) {
  const modo = item.proveniencia?.modo || item.fonteVerificacao;
  if (modo === 'verificacao_manual' || modo === 'portal_publico_terceiro') return 'Verificação manual · confirme valor e disponibilidade no anúncio';
  if (modo === 'coleta_automatica' || item.coletaAutomaticaPermitida === true) return 'Coleta automática da fonte cadastrada';
  return item.url ? 'Dados vinculados ao anúncio original' : null;
}
function temOportunidadeForte(item) {
  const o = item.elegibilidade?.oportunidade;
  return Boolean(o && (typeof o === 'string' ? o.trim() : Object.keys(o).length));
}
function faixaPreco(item) {
  const p = Number(item.aluguel);
  if (!Number.isFinite(p)) return null;
  if (p >= 2000 && p <= 3000) return 'Faixa principal';
  if (p >= 3001 && p <= 3500 && item.elegibilidade?.elegivel === true && temOportunidadeForte(item)) return 'Oportunidade excepcional';
  if (p < 2000) return temOportunidadeForte(item) && item.elegibilidade?.elegivel === true ? 'Oportunidade abaixo da faixa' : 'Abaixo da faixa de referência';
  if (p > 3500) return 'Acima do teto de R$ 3.500';
  return 'Fora da faixa principal';
}
function matchDisponivel(item) {
  const m = item.match || {};
  const componentes = [m.casa, m.localizacao, m.custoBeneficio, m.visual];
  return item.elegibilidade?.status !== 'pendente'
    && m.confianca !== 'incompleta'
    && componentes.every(v => Number.isFinite(Number(v)))
    && Number.isFinite(Number(m.final));
}
function areaExternaTexto(item) {
  if (item.areaExternaPrivativa === true || item.quintal === true) return '✓ Confirmada';
  if (item.areaExternaPrivativa === false || item.quintal === false) return '✕ Não';
  return 'A confirmar';
}

function renderImoveis() {
  const lista = document.querySelector('#lista');
  const rows = filtrar(state.imoveis.filter(ativo));
  lista.className = 'lista';
  lista.innerHTML = '';
  if (!rows.length) {
    const msg = state.tab === 'novos' ? 'Nenhum imóvel novo desde sua última revisão.' : 'Nenhuma casa aqui ainda.';
    lista.innerHTML = `<div class="vazio"><strong>${msg}</strong><span>Use “Todos” para consultar o inventário acompanhado.</span></div>`;
    return;
  }

  const tpl = document.querySelector('#cardTemplate');
  rows.forEach(item => {
    const node = tpl.content.cloneNode(true);
    const card = node.querySelector('.card');
    const d = decisao(item.id);
    const pendente = precisaConfirmacao(item);
    if (d === 'favorito') card.classList.add('favorito-card');
    if (pendente) card.classList.add('pendente-card');

    const fotos = fotosConfiaveis(item);
    if (fotos.length) {
      const wrap = node.querySelector('.foto-wrap');
      const img = node.querySelector('.foto');
      img.src = fotos[0];
      img.alt = `Foto real do imóvel em ${valor(item.bairro, 'Divinópolis')}`;
      img.addEventListener('error', () => { wrap.hidden = true; });
      wrap.hidden = false;
      wrap.dataset.galeria = fotos.length > 1 ? `${fotos.length} fotos reais` : 'Foto real';
    }

    node.querySelector('.fonte').textContent = [item.fonte, item.codigoFonte ? `cód. ${item.codigoFonte}` : null].filter(Boolean).join(' · ') || 'Fonte a confirmar';
    const qualidade = node.querySelector('.qualidade');
    qualidade.textContent = pendente ? 'A confirmar' : item.elegibilidade?.elegivel === true ? 'Elegível' : 'Fora dos critérios';
    qualidade.dataset.tipo = pendente ? 'pendente' : item.elegibilidade?.elegivel === true ? 'elegivel' : 'confirmado';
    node.querySelector('.titulo').textContent = valor(item.titulo, item.bairro ? `Casa em ${item.bairro}` : 'Casa para aluguel');
    node.querySelector('.local').textContent = [item.bairro, item.cidade].filter(Boolean).join(' · ') || 'Localização a confirmar';

    const match = node.querySelector('.match');
    if (!matchDisponivel(item)) {
      match.classList.add('match-pendente');
      match.innerHTML = '<strong>—</strong><span>Match incompleto</span>';
    } else {
      match.innerHTML = `<strong>${Number(item.match.final).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}</strong><span>Match</span>`;
    }

    node.querySelector('.metricas').innerHTML = [
      metric('aluguel', item.aluguel != null ? fmt.format(item.aluguel) : '—'),
      metric('quartos', valor(item.quartos)),
      metric('banheiros', valor(item.banheiros)),
      metric('área', item.areaM2 != null ? `${item.areaM2} m²` : '—'),
      metric('área externa', areaExternaTexto(item), 'metrica-externa')
    ].join('');

    const detalhes = [
      distanciaHospital(item),
      faixaPreco(item),
      item.vagas != null ? `${item.vagas} vaga${Number(item.vagas) === 1 ? '' : 's'}` : null
    ].filter(Boolean);
    node.querySelector('.detalhes').innerHTML = detalhes.map(x => `<span>${x}</span>`).join('');

    const alertas = [];
    if (item.elegibilidade?.status === 'inelegivel') {
      const motivo = (item.elegibilidade?.motivos || [])[0];
      alertas.push(motivo ? `Fora dos critérios: ${motivo}` : 'Fora dos critérios mínimos');
    } else if (item.elegibilidade?.status === 'pendente') {
      const faltas = (item.elegibilidade?.pendencias || []).slice(0, 3).map(x => x.replace(/ não confirmad[ao]$/i, '').replace(/ não informado$/i, ''));
      alertas.push(`Falta confirmar: ${faltas.length ? faltas.join(' · ') : 'requisitos mínimos'}`);
    }
    if (!fotos.length) alertas.push('Sem foto real disponível na fonte');
    else if (item.match?.visual == null) alertas.push('Foto real disponível · avaliação visual ainda não calculada');
    node.querySelector('.alertas').innerHTML = alertas.slice(0, 2).map(x => `<span>${x}</span>`).join('');

    const origem = origemTexto(item);
    const prov = node.querySelector('.proveniencia');
    const visto = dataPtBr(item.ultimoVistoEm);
    const provPartes = [origem, visto ? `Última confirmação: ${visto}` : null].filter(Boolean);
    if (provPartes.length) { prov.textContent = provPartes.join(' · '); prov.hidden = false; }

    const link = node.querySelector('.link');
    link.href = item.url || '#';
    if (!item.url) { link.classList.add('desativado'); link.textContent = 'Anúncio indisponível'; }

    const fav = node.querySelector('.favoritar');
    const descartar = node.querySelector('.descartar');
    if (d === 'favorito') {
      fav.textContent = '↩ Remover favorito';
      fav.addEventListener('click', () => setDecisao(item.id, null));
      descartar.textContent = '🗑 Descartar';
      descartar.addEventListener('click', () => setDecisao(item.id, 'descartado'));
    } else if (d === 'descartado') {
      fav.textContent = '♡ Favoritar';
      fav.addEventListener('click', () => setDecisao(item.id, 'favorito'));
      descartar.textContent = '↩ Restaurar';
      descartar.addEventListener('click', () => setDecisao(item.id, null));
    } else {
      fav.textContent = '♡ Favoritar';
      fav.addEventListener('click', () => setDecisao(item.id, 'favorito'));
      descartar.textContent = '🗑 Descartar';
      descartar.addEventListener('click', () => setDecisao(item.id, 'descartado'));
    }
    lista.appendChild(node);
  });
}

function statusFonte(fonte) {
  if (fonte.coletaAutomatica === true) return ['Coleta automática', 'automatico'];
  const s = String(fonte.status || '');
  if (s.includes('nao_automatizar') || s.includes('sem_automacao')) return ['Acesso direto · sem automação', 'manual'];
  if (s.includes('catalogo_') || s.includes('manual_verificado') || s.includes('auditoria_avancada') || s.includes('identidade_site_confirmados')) return ['Acesso direto · no radar', 'radar'];
  if (fonte.siteUrl) return ['Acesso direto · em validação', 'validacao'];
  return ['Em validação', 'validacao'];
}
function renderImobiliarias() {
  const lista = document.querySelector('#lista');
  lista.className = 'lista-fontes';
  const imobiliarias = state.fontes.filter(f => f.tipo === 'imobiliaria').sort((a,b) => a.nome.localeCompare(b.nome, 'pt-BR'));
  if (!imobiliarias.length) {
    lista.innerHTML = '<div class="vazio"><strong>Nenhuma imobiliária carregada.</strong></div>';
    return;
  }
  const automaticas = imobiliarias.filter(f => f.coletaAutomatica === true).length;
  const comSite = imobiliarias.filter(f => Boolean(f.siteUrl)).length;
  lista.innerHTML = `<div class="fontes-intro"><strong>Imobiliárias de Divinópolis no radar</strong><span>${imobiliarias.length} operações identificadas · ${comSite} com acesso direto · ${automaticas} com coleta automática autorizada. As demais ficam disponíveis para consulta manual enquanto política e catálogo são validados.</span></div>` + imobiliarias.map(fonte => {
    const [status, tipo] = statusFonte(fonte);
    const link = fonte.siteUrl ? `<a href="${fonte.siteUrl}" target="_blank" rel="noopener noreferrer">Abrir site</a>` : '<span class="sem-link">Site oficial ainda não identificado</span>';
    return `<article class="fonte-card"><div><strong>${fonte.nome}</strong><span class="fonte-status" data-tipo="${tipo}">${status}</span></div><p>${fonte.motivo || 'Operação local identificada; catálogo e política de coleta ainda em validação.'}</p>${link}</article>`;
  }).join('');
}

function render() {
  renderResumo();
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('ativo', b.dataset.tab === state.tab));
  const filtros = document.querySelector('#filtros');
  filtros.hidden = state.tab === 'imobiliarias';
  const marcar = document.querySelector('#marcarNovosVistos');
  marcar.hidden = state.tab !== 'novos' || state.novosIds.size === 0;
  if (state.tab === 'imobiliarias') renderImobiliarias();
  else renderImoveis();
}

function textoStatus(inv, status, fontesData) {
  const acompanhados = (inv.imoveis || []).filter(ativo).length;
  const atualizado = dataPtBr(inv.atualizadoEm || status?.fim);
  const fontes = fontesData?.fontes || [];
  const imobiliarias = fontes.filter(f => f.tipo === 'imobiliaria');
  const automaticasAtivas = imobiliarias.filter(f => f.coletaAutomatica === true).length;
  const partes = [`${acompanhados} anúncios acompanhados`];
  if (imobiliarias.length) partes.push(`${imobiliarias.length} imobiliárias no radar`);
  if (automaticasAtivas) partes.push(`${automaticasAtivas} fonte${automaticasAtivas === 1 ? '' : 's'} automática${automaticasAtivas === 1 ? '' : 's'} ativa${automaticasAtivas === 1 ? '' : 's'}`);
  if (status && Number(status.imoveisComFotos || 0) > 0) partes.push(`${Number(status.imoveisComFotos)} com foto real na coleta atual`);
  if (atualizado) partes.push(`atualizado em ${atualizado}`);
  return partes.join(' · ');
}

async function carregar() {
  try {
    const [inv, status, fontesData] = await Promise.all([
      fetch('data/imoveis.json', { cache: 'no-store' }).then(r => r.json()),
      fetch('data/status-coleta.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('data/fontes.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : { fontes: [] }).catch(() => ({ fontes: [] }))
    ]);
    state.imoveis = inv.imoveis || [];
    state.fontes = fontesData.fontes || [];
    inicializarNovos(state.imoveis);
    const idsAtivos = new Set(state.imoveis.map(i => i.id).filter(Boolean));
    const limpas = Object.fromEntries(Object.entries(state.decisoes).filter(([id]) => idsAtivos.has(id)));
    if (Object.keys(limpas).length !== Object.keys(state.decisoes).length) { state.decisoes = limpas; salvarDecisoes(); }
    const el = document.querySelector('#statusColeta');
    el.textContent = textoStatus(inv, status, fontesData);
    if (status?.estado) el.dataset.estado = status.estado;
    render();
  } catch {
    document.querySelector('#statusColeta').textContent = 'Não foi possível carregar os dados';
    document.querySelector('#lista').innerHTML = '<div class="vazio">Falha ao carregar a base publicada.</div>';
  }
}

document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => { state.tab = b.dataset.tab; render(); }));
document.querySelector('#ordenacao').addEventListener('change', render);
document.querySelector('#somenteElegiveis').addEventListener('change', render);
document.querySelector('#marcarNovosVistos').addEventListener('click', marcarNovosComoVistos);
carregar();