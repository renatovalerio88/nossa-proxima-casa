function carregarDecisoes() {
  try {
    const bruto = JSON.parse(localStorage.getItem('npc-decisoes') || '{}');
    if (!bruto || typeof bruto !== 'object' || Array.isArray(bruto)) return {};
    return Object.fromEntries(Object.entries(bruto).filter(([, v]) => v === 'favorito' || v === 'descartado'));
  } catch {
    return {};
  }
}

const state = { tab: 'novos', imoveis: [], decisoes: carregarDecisoes() };
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
  const d = new Date(v.includes('T') ? v : `${v}T12:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric' }).format(d);
}
function ehNovo(item) {
  if (!item.primeiroVistoEm) return false;
  const d = new Date(item.primeiroVistoEm.includes('T') ? item.primeiroVistoEm : `${item.primeiroVistoEm}T12:00:00`);
  if (Number.isNaN(d.getTime())) return false;
  const idade = Date.now() - d.getTime();
  return idade >= 0 && idade <= 7 * 86400000;
}
function precisaConfirmacao(item) { return item.elegibilidade?.status === 'pendente'; }
function ativo(item) { return item.disponivel !== false; }

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
    if (ordem === 'preco') return (a.aluguel ?? Infinity) - (b.aluguel ?? Infinity);
    if (ordem === 'recente') {
      const data = String(b.primeiroVistoEm || '').localeCompare(String(a.primeiroVistoEm || ''));
      return data !== 0 ? data : (b.match?.final ?? -1) - (a.match?.final ?? -1);
    }
    return (b.match?.final ?? -1) - (a.match?.final ?? -1);
  });
}

function metric(label, value) { return `<div><strong>${value}</strong><span>${label}</span></div>`; }
function renderResumo() {
  const ativos = state.imoveis.filter(ativo);
  const elegiveis = ativos.filter(i => i.elegibilidade?.elegivel === true).length;
  const confirmar = ativos.filter(i => precisaConfirmacao(i)).length;
  const fav = ativos.filter(i => decisao(i.id) === 'favorito').length;
  const novos = ativos.filter(i => ehNovo(i) && decisao(i.id) === null).length;
  document.querySelector('#resumo').innerHTML = [
    metric('elegíveis confirmados', elegiveis),
    metric('novos em 7 dias', novos),
    metric('a confirmar', confirmar),
    metric('favoritas', fav)
  ].join('');
}

function ultimoEventoPreco(item) {
  const eventos = (item.historico || []).filter(e => e.campo === 'aluguel');
  return eventos.length ? eventos[eventos.length - 1] : null;
}
function distanciaHospital(item) {
  const hospital = item.hospital || {};
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
function detalhe(label, value) { return value == null || value === '' ? null : `${label}: ${value}`; }
function origemTexto(item) {
  const modo = item.proveniencia?.modo || item.fonteVerificacao;
  if (modo === 'verificacao_manual' || modo === 'portal_publico_terceiro') return 'Verificação manual · confirme valor e disponibilidade no anúncio';
  if (modo === 'coleta_automatica' || item.coletaAutomaticaPermitida === true) return 'Coleta automática da fonte cadastrada';
  return item.url ? 'Dados vinculados ao anúncio original' : null;
}
function faixaPreco(item) {
  const p = Number(item.aluguel);
  if (!Number.isFinite(p)) return null;
  if (p >= 2000 && p <= 3000) return 'Faixa principal';
  if (p >= 3001 && p <= 3500 && item.elegibilidade?.elegivel === true) return 'Oportunidade acima da faixa';
  if (p < 2000 && item.elegibilidade?.elegivel === true) return 'Oportunidade abaixo da faixa';
  return null;
}
function matchDisponivel(item) {
  return !precisaConfirmacao(item) && Number.isFinite(Number(item.match?.final));
}

function render() {
  renderResumo();
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('ativo', b.dataset.tab === state.tab));
  const lista = document.querySelector('#lista');
  const rows = filtrar(state.imoveis.filter(ativo));
  lista.innerHTML = '';
  if (!rows.length) {
    const msg = state.tab === 'novos' ? 'Nenhum imóvel novo nos últimos 7 dias.' : 'Nenhuma casa aqui ainda.';
    lista.innerHTML = `<div class="vazio"><strong>${msg}</strong><span>Use “Todos” para consultar o inventário ativo completo.</span></div>`;
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
      if (fotos.length > 1) wrap.dataset.galeria = `${fotos.length} fotos reais`;
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
      metric('área', item.areaM2 != null ? `${item.areaM2} m²` : '—')
    ].join('');

    const detalhes = [
      item.areaExternaPrivativa === true || item.quintal === true ? '✓ Área externa privativa' : null,
      item.vagas != null ? `${item.vagas} vaga${Number(item.vagas) === 1 ? '' : 's'}` : null,
      distanciaHospital(item),
      faixaPreco(item)
    ].filter(Boolean);
    node.querySelector('.detalhes').innerHTML = detalhes.map(x => `<span>${x}</span>`).join('');

    const descricao = node.querySelector('.descricao');
    descricao.hidden = true;

    const alertas = [];
    if (ehNovo(item)) alertas.push('● Novo nos últimos 7 dias');
    if (item.elegibilidade?.status === 'pendente') alertas.push('⚠ Requisitos mínimos ainda não confirmados');
    if (item.elegibilidade?.status === 'inelegivel') alertas.push('✕ Fora dos critérios mínimos');
    (item.elegibilidade?.motivos || []).slice(0, 1).forEach(x => alertas.push(`✕ ${x}`));
    (item.elegibilidade?.pendencias || []).slice(0, 2).forEach(x => alertas.push(`⚠ ${x}`));
    if (!fotos.length) alertas.push('Avaliação visual indisponível · sem fotos reais');
    else if (item.match?.visual == null) alertas.push('Fotos reais disponíveis · avaliação visual ainda não calculada');

    const ultimoPreco = ultimoEventoPreco(item);
    if (ultimoPreco?.para != null) {
      const de = ultimoPreco.de != null ? fmt.format(ultimoPreco.de) : 'não informado';
      alertas.push(`Preço: ${de} → ${fmt.format(ultimoPreco.para)}`);
    }
    node.querySelector('.alertas').innerHTML = alertas.slice(0, 4).map(x => `<span>${x}</span>`).join('');

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

function textoStatus(inv, status) {
  const ativos = (inv.imoveis || []).filter(ativo).length;
  const atualizado = dataPtBr(inv.atualizadoEm || status?.fim);
  if (!status) return `${ativos} imóveis ativos${atualizado ? ` · atualizado em ${atualizado}` : ''}`;
  const fontes = Object.entries(status.fontes || {});
  const fontesComSucesso = fontes.filter(([,v]) => Number(v.sucessos || 0) > 0).length;
  const fontesTentadas = fontes.length;
  const partes = [`${ativos} imóveis ativos`];
  if (fontesTentadas) partes.push(`${fontesComSucesso}/${fontesTentadas} fonte${fontesTentadas === 1 ? '' : 's'} com retorno nesta atualização`);
  if (atualizado) partes.push(`atualizado em ${atualizado}`);
  return partes.join(' · ');
}

async function carregar() {
  try {
    const [inv, status] = await Promise.all([
      fetch('data/imoveis.json', { cache: 'no-store' }).then(r => r.json()),
      fetch('data/status-coleta.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null)
    ]);
    state.imoveis = inv.imoveis || [];
    const idsAtivos = new Set(state.imoveis.map(i => i.id).filter(Boolean));
    const limpas = Object.fromEntries(Object.entries(state.decisoes).filter(([id]) => idsAtivos.has(id)));
    if (Object.keys(limpas).length !== Object.keys(state.decisoes).length) { state.decisoes = limpas; salvarDecisoes(); }
    const el = document.querySelector('#statusColeta');
    el.textContent = textoStatus(inv, status);
    if (status?.estado) el.dataset.estado = status.estado;
    render();
  } catch {
    document.querySelector('#statusColeta').textContent = 'Não foi possível carregar os dados';
    document.querySelector('#lista').innerHTML = '<div class="vazio">Falha ao carregar a base publicada.</div>';
  }
}

document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => { state.tab = b.dataset.tab; render(); b.scrollIntoView({ behavior:'smooth', block:'nearest', inline:'center' }); }));
document.querySelector('#ordenacao').addEventListener('change', render);
document.querySelector('#somenteElegiveis').addEventListener('change', render);
carregar();