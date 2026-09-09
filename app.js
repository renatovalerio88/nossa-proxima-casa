const state = {
  tab: 'novos',
  imoveis: [],
  decisoes: JSON.parse(localStorage.getItem('npc-decisoes') || '{}')
};

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function salvarDecisoes() {
  localStorage.setItem('npc-decisoes', JSON.stringify(state.decisoes));
}

function decisao(id) {
  return state.decisoes[id] || null;
}

function setDecisao(id, valor) {
  if (valor === null || decisao(id) === valor) delete state.decisoes[id];
  else state.decisoes[id] = valor;
  salvarDecisoes();
  render();
}

function valor(v, fallback = '—') {
  return v === null || v === undefined || v === '' ? fallback : v;
}

function dataPtBr(v) {
  if (!v) return null;
  const d = new Date(`${v}T12:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat('pt-BR').format(d);
}

function ehNovo(item) {
  if (!item.primeiroVistoEm) return true;
  const d = new Date(`${item.primeiroVistoEm}T12:00:00`);
  if (Number.isNaN(d.getTime())) return true;
  return (Date.now() - d.getTime()) <= 7 * 86400000;
}

function filtrar(items) {
  const somenteElegiveis = document.querySelector('#somenteElegiveis').checked;
  let rows = items.filter(i => !somenteElegiveis || i.elegibilidade?.elegivel === true);
  rows = rows.filter(i => {
    const d = decisao(i.id);
    if (state.tab === 'favoritados') return d === 'favorito';
    if (state.tab === 'descartados') return d === 'descartado';
    if (state.tab === 'novos') return d === null;
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

function metric(label, value) {
  return `<div><strong>${value}</strong><span>${label}</span></div>`;
}

function renderResumo() {
  const ativos = state.imoveis.filter(i => i.disponivel !== false);
  const fav = ativos.filter(i => decisao(i.id) === 'favorito').length;
  const novos = ativos.filter(i => ehNovo(i) && decisao(i.id) === null).length;
  document.querySelector('#resumo').innerHTML = [
    metric('casas ativas', ativos.length),
    metric('novas em 7 dias', novos),
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
  if (km === null || km === undefined) return null;
  const aproximada = hospital.precisaoLocalizacao === 'bairro';
  const sufixo = aproximada ? ' (aprox. pelo bairro)' : '';
  return `Hospital: ~${Number(km).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} km${sufixo}`;
}

function render() {
  renderResumo();
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('ativo', b.dataset.tab === state.tab));
  const lista = document.querySelector('#lista');
  const rows = filtrar(state.imoveis.filter(i => i.disponivel !== false));
  lista.innerHTML = '';
  if (!rows.length) {
    lista.innerHTML = '<div class="vazio"><strong>Nenhuma casa aqui ainda.</strong><span>Assim que a coleta encontrar imóveis válidos, eles aparecerão automaticamente.</span></div>';
    return;
  }

  const tpl = document.querySelector('#cardTemplate');
  rows.forEach(item => {
    const node = tpl.content.cloneNode(true);
    const card = node.querySelector('.card');
    const d = decisao(item.id);
    if (d === 'favorito') card.classList.add('favorito-card');
    node.querySelector('.fonte').textContent = `${valor(item.fonte, 'Fonte')} · cód. ${valor(item.codigoFonte)}`;
    node.querySelector('.titulo').textContent = valor(item.titulo, 'Casa para aluguel');
    node.querySelector('.local').textContent = [item.bairro, item.cidade].filter(Boolean).join(' · ') || 'Localização a confirmar';
    const match = node.querySelector('.match');
    match.innerHTML = `<strong>${valor(item.match?.final)}</strong><span>Match</span>`;
    node.querySelector('.metricas').innerHTML = [
      metric('aluguel', item.aluguel != null ? fmt.format(item.aluguel) : '—'),
      metric('área', item.areaM2 != null ? `${item.areaM2} m²` : '—'),
      metric('quartos', valor(item.quartos)),
      metric('vagas', valor(item.vagas))
    ].join('');

    const alertas = [];
    if (ehNovo(item)) alertas.push('● Novo nos últimos 7 dias');

    const primeiro = dataPtBr(item.primeiroVistoEm);
    const ultimo = dataPtBr(item.ultimoVistoEm);
    if (primeiro) alertas.push(`Visto desde ${primeiro}`);
    if (ultimo && ultimo !== primeiro) alertas.push(`Última confirmação ${ultimo}`);

    const ultimoPreco = ultimoEventoPreco(item);
    if (ultimoPreco && ultimoPreco.para != null) {
      const de = ultimoPreco.de != null ? fmt.format(ultimoPreco.de) : 'não informado';
      const para = fmt.format(ultimoPreco.para);
      alertas.push(`Preço alterado: ${de} → ${para}`);
    }

    const statusElegibilidade = item.elegibilidade?.status;
    if (statusElegibilidade === 'elegivel') alertas.push('✓ Critérios mínimos confirmados');
    if (statusElegibilidade === 'pendente') alertas.push('⚠ Dados obrigatórios a confirmar');
    if (statusElegibilidade === 'inelegivel') alertas.push('✕ Fora dos critérios mínimos');
    (item.elegibilidade?.motivos || []).forEach(x => alertas.push(`✕ ${x}`));
    (item.elegibilidade?.pendencias || []).forEach(x => alertas.push(`⚠ ${x}`));

    if (item.quintal === true) alertas.push('✓ Quintal');
    if (item.armarios === true) alertas.push('✓ Armários');
    const hospitalKm = distanciaHospital(item);
    if (hospitalKm) alertas.push(hospitalKm);

    if (item.match) {
      const partes = [
        ['Casa', item.match.casa],
        ['Localização', item.match.localizacao],
        ['Custo', item.match.custoBeneficio],
        ['Visual', item.match.visual]
      ].filter(([, v]) => v !== null && v !== undefined);
      if (partes.length) alertas.push(`Match: ${partes.map(([k, v]) => `${k} ${v}`).join(' · ')}`);
    }

    (item.match?.pontosAtencao || []).slice(0,2).forEach(x => alertas.push(`⚠ ${x}`));
    node.querySelector('.alertas').innerHTML = alertas.map(x => `<span>${x}</span>`).join('');

    const link = node.querySelector('.link');
    link.href = item.url || '#';
    if (!item.url) link.classList.add('desativado');

    const fav = node.querySelector('.favoritar');
    const descartar = node.querySelector('.descartar');
    if (d === 'favorito') {
      fav.textContent = '↩ Voltar para Novos';
      fav.addEventListener('click', () => setDecisao(item.id, null));
      descartar.textContent = '🗑 Descartar';
      descartar.addEventListener('click', () => setDecisao(item.id, 'descartado'));
    } else if (d === 'descartado') {
      fav.textContent = '♡ Favoritar';
      fav.addEventListener('click', () => setDecisao(item.id, 'favorito'));
      descartar.textContent = '↩ Voltar para Novos';
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

async function carregar() {
  try {
    const [inv, status] = await Promise.all([
      fetch('data/imoveis.json', { cache: 'no-store' }).then(r => r.json()),
      fetch('data/status-coleta.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null)
    ]);
    state.imoveis = inv.imoveis || [];
    const el = document.querySelector('#statusColeta');
    if (!status) el.textContent = `Base atualizada: ${valor(inv.atualizadoEm, 'aguardando primeira coleta')}`;
    else {
      const texto = status.estado === 'ok' ? 'Coleta saudável' : status.estado === 'parcial' ? 'Coleta parcial' : 'Fontes temporariamente indisponíveis';
      el.textContent = `${texto} · ${status.coletados} capturado(s)`;
      el.dataset.estado = status.estado;
    }
    render();
  } catch (err) {
    document.querySelector('#statusColeta').textContent = 'Não foi possível carregar os dados';
    document.querySelector('#lista').innerHTML = '<div class="vazio">Falha ao carregar a base publicada.</div>';
  }
}

document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => { state.tab = b.dataset.tab; render(); }));
document.querySelector('#ordenacao').addEventListener('change', render);
document.querySelector('#somenteElegiveis').addEventListener('change', render);
carregar();
