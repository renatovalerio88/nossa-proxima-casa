function disponivelNaFonte(item) {
  return item?.disponivel !== false;
}

function temJustificativaOportunidade(item) {
  const oportunidade = item?.elegibilidade?.oportunidade;
  if (typeof oportunidade === 'string') return oportunidade.trim().length > 0;
  return Boolean(oportunidade && typeof oportunidade === 'object' && Object.keys(oportunidade).length);
}

function temJustificativaForteAbaixoDoPiso(item) {
  const oportunidade = item?.elegibilidade?.oportunidade;
  if (!oportunidade || typeof oportunidade !== 'object') return false;

  const nivel = String(oportunidade.nivel || oportunidade.forca || oportunidade.classificacao || '').toLowerCase();
  const marcadaForte = oportunidade.forte === true || ['forte', 'alta', 'excepcional'].includes(nivel);
  const motivos = Array.isArray(oportunidade.motivos) ? oportunidade.motivos.filter(Boolean) : [];
  const justificativa = String(oportunidade.justificativa || oportunidade.texto || '').trim();

  // Abaixo de R$ 2 mil não basta um rótulo genérico: exige marcação explícita de força
  // e evidência concreta registrada em motivos ou justificativa substancial.
  return marcadaForte && (motivos.length >= 2 || justificativa.length >= 80);
}

function candidatoAtivo(item) {
  if (!disponivelNaFonte(item)) return false;

  const elegibilidade = item?.elegibilidade || {};
  const preco = Number(item?.aluguel);

  // Imóvel já reprovado pelos critérios oficiais nunca permanece no radar ativo.
  if (elegibilidade.status === 'inelegivel') return false;

  if (!Number.isFinite(preco)) {
    // Preço desconhecido pode continuar apenas como "A confirmar".
    return elegibilidade.status === 'pendente';
  }

  // Acima do teto absoluto não é candidato ativo, embora continue preservado no inventário/histórico.
  if (preco > 3500) return false;

  // Abaixo de R$ 2.000 a exceção é realmente excepcional: mínimos confirmados + justificativa forte estruturada.
  if (preco < 2000) {
    return elegibilidade.elegivel === true && temJustificativaForteAbaixoDoPiso(item);
  }

  // Entre R$ 3.001 e R$ 3.500 a oportunidade também precisa estar objetiva e com mínimos confirmados.
  if (preco > 3000) {
    return elegibilidade.elegivel === true && temJustificativaOportunidade(item);
  }

  // Entre R$ 2.000 e R$ 3.000, elegíveis e pendentes permanecem no radar para validação.
  return elegibilidade.status === 'elegivel' || elegibilidade.status === 'pendente';
}

// app.js usa a função global ativo() em Novos, Todos, Favoritados, Descartados e A confirmar.
// Substituímos apenas a semântica de "ativo"; disponibilidade da fonte continua preservada separadamente.
ativo = candidatoAtivo;

function prioridadeFaixaPrincipal(item) {
  const preco = Number(item?.aluguel);
  if (!Number.isFinite(preco)) return 2;
  return preco >= 2000 && preco <= 3000 ? 0 : 1;
}

function matchConfiavel(item) {
  const m = item?.match || {};
  const componentes = [m.casa, m.localizacao, m.custoBeneficio, m.visual];
  return item?.elegibilidade?.status !== 'pendente'
    && m.confianca !== 'incompleta'
    && componentes.every(v => Number.isFinite(Number(v)))
    && Number.isFinite(Number(m.final));
}

function prioridadeQualidade(item) {
  // Não cria nota. Apenas usa sinais reais já existentes como desempate.
  const temMatch = matchConfiavel(item) ? 0 : 1;
  const temFoto = typeof fotosConfiaveis === 'function' && fotosConfiaveis(item).length > 0 ? 0 : 1;
  const hospitalValidado = item?.hospital?.localizacaoValidada === true ? 0 : 1;
  return [temMatch, temFoto, hospitalValidado];
}

// Mínimos confirmados continuam acima de pendências, mas dentro de cada grupo a faixa principal vem primeiro.
// Assim, oportunidades abaixo de R$ 2.000 ou entre R$ 3.001–3.500 permanecem consultáveis sem dominar o ranking.
prioridadeCandidato = function prioridadeCandidatoComFaixa(item) {
  const elegibilidade = item?.elegibilidade || {};
  const nivel = elegibilidade.elegivel === true ? 0 : precisaConfirmacao(item) ? 10 : 20;
  return nivel + prioridadeFaixaPrincipal(item);
};

filtrar = function filtrarComPolitica(items) {
  const somenteElegiveis = document.querySelector('#somenteElegiveis').checked;
  let rows = items.filter(i => candidatoAtivo(i) && (!somenteElegiveis || i.elegibilidade?.elegivel === true));

  rows = rows.filter(i => {
    const d = decisao(i.id);
    if (state.tab === 'favoritados') return d === 'favorito';
    if (state.tab === 'descartados') return d === 'descartado';
    if (state.tab === 'a-confirmar') return d === null && precisaConfirmacao(i);
    if (state.tab === 'novos') return d === null && ehNovo(i);
    return true;
  });

  const ordem = document.querySelector('#ordenacao').value;
  return rows.sort((a, b) => {
    const prioridade = prioridadeCandidato(a) - prioridadeCandidato(b);
    if (prioridade !== 0) return prioridade;

    // Fora da faixa principal nunca ganha de candidato equivalente da faixa apenas por preço ou Match.
    const faixa = prioridadeFaixaPrincipal(a) - prioridadeFaixaPrincipal(b);
    if (faixa !== 0) return faixa;

    if (ordem === 'preco') return (a.aluguel ?? Infinity) - (b.aluguel ?? Infinity);

    if (ordem === 'match') {
      const aTem = matchConfiavel(a);
      const bTem = matchConfiavel(b);
      if (aTem !== bTem) return aTem ? -1 : 1;
      if (aTem && bTem) {
        const diff = Number(b.match.final) - Number(a.match.final);
        if (diff !== 0) return diff;
      }
    }

    // Em "Mais relevantes e recentes", preferência por informação real mais completa, sem fabricar nota.
    if (ordem === 'recente') {
      const qa = prioridadeQualidade(a);
      const qb = prioridadeQualidade(b);
      for (let i = 0; i < qa.length; i += 1) {
        if (qa[i] !== qb[i]) return qa[i] - qb[i];
      }
      const data = String(b.primeiroVistoEm || '').localeCompare(String(a.primeiroVistoEm || ''));
      if (data !== 0) return data;
      if (matchConfiavel(a) && matchConfiavel(b)) return Number(b.match.final) - Number(a.match.final);
    }

    return 0;
  });
};

renderResumo = function renderResumoComPoliticaDeCandidatos() {
  const acompanhados = state.imoveis.filter(disponivelNaFonte);
  const candidatos = acompanhados.filter(candidatoAtivo);
  const minimosOk = candidatos.filter(i => i.elegibilidade?.elegivel === true).length;
  const confirmar = candidatos.filter(i => precisaConfirmacao(i)).length;
  const foraRadar = acompanhados.filter(i => !candidatoAtivo(i)).length;

  document.querySelector('#resumo').innerHTML = [
    metric('candidatos ativos', candidatos.length),
    metric('mínimos OK', minimosOk),
    metric('a confirmar', confirmar),
    metric('fora do radar ativo', foraRadar)
  ].join('');

  const fav = candidatos.filter(i => decisao(i.id) === 'favorito').length;
  const novosVisiveis = candidatos.filter(i => decisao(i.id) === null && i?.id && state.novosIds.has(i.id)).length;
  document.querySelector('[data-tab="favoritados"]').textContent = fav ? `Favoritados (${fav})` : 'Favoritados';
  document.querySelector('[data-tab="novos"]').textContent = novosVisiveis ? `Novos (${novosVisiveis})` : 'Novos';
};

textoStatus = function textoStatusComRadar(inv, status, fontesData) {
  const disponiveis = (inv.imoveis || []).filter(disponivelNaFonte);
  const candidatos = disponiveis.filter(candidatoAtivo).length;
  const minimosOk = disponiveis.filter(i => candidatoAtivo(i) && i.elegibilidade?.elegivel === true).length;
  const atualizado = dataPtBr(inv.atualizadoEm || status?.fim);
  const fontes = fontesData?.fontes || [];
  const imobiliarias = fontes.filter(f => f.tipo === 'imobiliaria');
  const automaticasAtivas = imobiliarias.filter(f => f.coletaAutomatica === true).length;
  const partes = [
    `${disponiveis.length} anúncios acompanhados`,
    `${candidatos} candidatos ativos`,
    `${minimosOk} mínimos OK`
  ];
  if (imobiliarias.length) partes.push(`${imobiliarias.length} imobiliárias no radar`);
  if (automaticasAtivas) partes.push(`${automaticasAtivas} fonte${automaticasAtivas === 1 ? '' : 's'} automática${automaticasAtivas === 1 ? '' : 's'} ativa${automaticasAtivas === 1 ? '' : 's'}`);
  if (status && Number(status.imoveisComFotos || 0) > 0) partes.push(`${Number(status.imoveisComFotos)} com foto real na coleta atual`);
  if (atualizado) partes.push(`atualizado em ${atualizado}`);
  return partes.join(' · ');
};
