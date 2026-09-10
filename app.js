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
  decisoes: carregarDecisoes()
};

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function salvarDecisoes() {
  try {
    localStorage.setItem('npc-decisoes', JSON.stringify(state.decisoes));
  } catch {
    // O painel continua funcional mesmo se o navegador bloquear armazenamento local.
  }
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

function precisaConfirmacao(item) {
  return item.elegibilidade?.status === 'pendente';
}

function filtrar(items) {
  const somenteElegiveis = document.querySelector('#somenteElegiveis').checked;
  let rows = items.filter(i => !somenteElegiveis || i.elegibilidade?.elegivel === true);
  rows = rows.filter(i => {
    const d = decisao(i.id);
    if (state.tab === 'favoritados') return d === 'favorito';
    if (state.tab === 'descartados') return d === 'descartado';
    if (state.tab === 'a-confirmar') return d === null && precisaConfirmacao(i);
    if (state.tab === 'novos') return d === null && !precisaConfirmacao(i);
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
  const avaliaveis = ativos.filter(i => !precisaConfirmacao(i)).length;
  const confirmar = ativos.filter(i => precisaConfirmacao(i)).length;
  const fav = ativos.filter(i => decisao(i.id) === 'favorito').length;
  const novos = ativos.filter(i => ehNovo(i) && decisao(i.id) === null && !precisaConfirmacao(i)).length;
  document.querySelector('#resumo').innerHTML = [
    metric('casas avaliáveis', avaliaveis),
    metric('novas em 7 dias', novos),
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
  const kmRota = hospital.distanciaKm;
  const kmLinhaReta = hospital.distanciaLinhaRetaKm;
  const km = kmRota ?? kmLinhaReta;
  if (km === null || km === undefined) return null;
  const aproximada = hospital.precisaoLocalizacao === 'bairro';
  const tipo = kmRota != null ? '' : ' em linha reta';
  const sufixo = aproximada ? ' (aprox. pelo bairro)' : '';
  return `Hospital: ~${Number(km).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} km${tipo}${sufixo}`;
}

function fotoConfiavel(item) {
  const candidatos = [
    item.fotoUrl,
    item.imagemUrl,
    ...(Array.isArray(item.fotos) ? item.fotos : []),
    ...(Array.isArray(item.imagens) ? item.imagens : [])
  ].filter(Boolean);
  return candidatos.find(url => /^https:\/\//i.test(String(url))) || null;
}

function detalhe(label, value) {
  if (value === null || value === undefined || value === '') return null;
  return `${label}: ${value}`;
}

function detalhesImovel(item) {
  return [
    detalhe('Suítes', item.suites),
    detalhe('Banheiros', item.banheiros),
    detalhe('Terreno', item.terrenoM2 != null ? `${item.terrenoM2} m²` : null),
    detalhe('Condomínio', item.condominio != null ? fmt.format(item.condominio) : null),
    detalhe('IPTU', item.iptu != null ? fmt.format(item.iptu) : null)
  ].filter(Boolean);
}

function origemTexto(item) {
  const modo = item.proveniencia?.modo || item.fonteVerificacao;
  if (modo === 'verificacao_manual' || modo === 'portal_publico_terceiro') return 'Verificação manual · confirme valor e disponibilidade no anúncio';
  if (modo === 'coleta_automatica' || item.coletaAutomaticaPermitida === true) return 'Coleta automática da fonte cadastrada';
  return item.url ? 'Dados vinculados ao anúncio original' : null;
}

function render() {
  renderResumo();
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('ativo', b.dataset.tab === state.tab));
  const lista = document.querySelector('#lista');
  const rows = filtrar(state.imoveis.filter(i => i.disponivel !== false));
  lista.innerHTML = '';
  if (!rows.length) {
    lista.innerHTML = '<div class="vazio"><strong>Nenhuma casa aqui ainda.</strong><span>Assim que houver um imóvel real nessa categoria, ele aparecerá automaticamente.</span></div>';
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

    const foto = fotoConfiavel(item);
    if (foto) {
      const wrap = node.querySelector('.foto-wrap');
      const img = node.querySelector('.foto');
      img.src = foto;
      img.alt = `Foto do imóvel em ${valor(item.bairro, 'Divinópolis')}`;
      img.addEventListener('error', () => { wrap.hidden = true; });
      wrap.hidden = false;
    }

    node.querySelector('.fonte').textContent = `${valor(item.fonte, 'Fonte')} · cód. ${valor(item.codigoFonte)}`;
    const qualidade = node.querySelector('.qualidade');
    qualidade.textContent = pendente ? 'A confirmar' : item.elegibilidade?.elegivel === true ? 'Elegível' : 'Dados confirmados';
    qualidade.dataset.tipo = pendente ? 'pendente' : item.elegibilidade?.elegivel === true ? 'elegivel' : 'confirmado';
    node.querySelector('.titulo').textContent = valor(item.titulo, item.bairro ? `Casa em ${item.bairro}` : 'Casa para aluguel');
    node.querySelector('.local').textContent = [item.endereco, item.bairro, item.cidade].filter(Boolean).join(' · ') || 'Localização a confirmar';

    const match = node.querySelector('.match');
    if (pendente) {
      match.classList.add('match-pendente');
      match.innerHTML = '<strong>—</strong><span>Match após confirmação</span>';
    } else {
      match.innerHTML = `<strong>${valor(item.match?.final)}</strong><span>Match</span>`;
    }

    node.querySelector('.metricas').innerHTML = [
      metric('aluguel', item.aluguel != null ? fmt.format(item.aluguel) : '—'),
      metric('área', item.areaM2 != null ? `${item.areaM2} m²` : '—'),
      metric('quartos', valor(item.quartos)),
      metric('vagas', valor(item.vagas))
    ].join('');

    const descricao = node.querySelector('.descricao');
    if (item.descricao) {
      descricao.textContent = item.descricao;
      descricao.hidden = false;
    }

    const detalhes = detalhesImovel(item);
    node.querySelector('.detalhes').innerHTML = detalhes.map(x => `<span>${x}</span>`).join('');

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
    if (item.churrasqueira === true) alertas.push('✓ Churrasqueira');
    if (item.piscina === true) alertas.push('✓ Piscina');
    if (item.hidromassagem === true) alertas.push('✓ Hidromassagem');
    const hospitalKm = distanciaHospital(item);
    if (hospitalKm) alertas.push(hospitalKm);

    if (item.match && !pendente) {
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

    const origem = origemTexto(item);
    const prov = node.querySelector('.proveniencia');
    if (origem) {
      prov.textContent = origem;
      prov.hidden = false;
    }

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
    const idsAtivos = new Set(state.imoveis.map(i => i.id).filter(Boolean));
    const limpas = Object.fromEntries(Object.entries(state.decisoes).filter(([id]) => idsAtivos.has(id)));
    if (Object.keys(limpas).length !== Object.keys(state.decisoes).length) {
      state.decisoes = limpas;
      salvarDecisoes();
    }

    const el = document.querySelector('#statusColeta');
    if (!status) el.textContent = `Base atualizada: ${valor(inv.atualizadoEm, 'aguardando primeira coleta')}`;
    else {
      const texto = status.estado === 'ok' ? 'Coleta saudável' : status.estado === 'parcial' ? 'Coleta parcial' : 'Fontes temporariamente indisponíveis';
      el.textContent = `${texto} · ${status.coletados} capturado(s)`;
      el.dataset.estado = status.estado;
    }
    render();
  } catch {
    document.querySelector('#statusColeta').textContent = 'Não foi possível carregar os dados';
    document.querySelector('#lista').innerHTML = '<div class="vazio">Falha ao carregar a base publicada.</div>';
  }
}

document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => { state.tab = b.dataset.tab; render(); }));
document.querySelector('#ordenacao').addEventListener('change', render);
document.querySelector('#somenteElegiveis').addEventListener('change', render);
carregar();
