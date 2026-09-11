function disponivelNaFonte(item) {
  return item?.disponivel !== false;
}

function temJustificativaOportunidade(item) {
  const oportunidade = item?.elegibilidade?.oportunidade;
  if (typeof oportunidade === 'string') return oportunidade.trim().length > 0;
  return Boolean(oportunidade && typeof oportunidade === 'object' && Object.keys(oportunidade).length);
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

  // Fora da faixa principal só entra quando a oportunidade já está objetiva e todos os mínimos foram confirmados.
  if (preco < 2000 || preco > 3000) {
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

// Mínimos confirmados continuam acima de pendências, mas dentro de cada grupo a faixa principal vem primeiro.
// Assim, oportunidades abaixo de R$ 2.000 ou entre R$ 3.001–3.500 permanecem consultáveis sem dominar o ranking.
prioridadeCandidato = function prioridadeCandidatoComFaixa(item) {
  const elegibilidade = item?.elegibilidade || {};
  const nivel = elegibilidade.elegivel === true ? 0 : precisaConfirmacao(item) ? 10 : 20;
  return nivel + prioridadeFaixaPrincipal(item);
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
