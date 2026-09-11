(() => {
  const renderBase = render;
  const textoStatusBase = textoStatus;

  function aplicarRotulos() {
    document.querySelectorAll('.qualidade[data-tipo="elegivel"]').forEach(el => {
      el.textContent = 'Mínimos OK';
      el.title = 'Quartos, banheiros, área mínima e área externa confirmados. Não significa recomendação final.';
    });
    document.querySelectorAll('.match-pendente span').forEach(el => {
      el.textContent = 'Match a calcular';
    });
    document.querySelectorAll('.proveniencia').forEach(el => {
      el.classList.add('proveniencia-secundaria');
    });
  }

  render = function renderUX() {
    renderBase();
    aplicarRotulos();
  };

  textoStatus = function textoStatusUX(inv, status, fontesData) {
    const ativos = (inv.imoveis || []).filter(ativo);
    const elegiveis = ativos.filter(i => i.elegibilidade?.elegivel === true).length;
    const atualizado = dataPtBr(inv.atualizadoEm || status?.fim);
    const partes = [`${ativos.length} casas no radar`, `${elegiveis} com mínimos confirmados`];
    if (atualizado) partes.push(`atualizado em ${atualizado}`);
    return partes.join(' · ');
  };

  statusFonte = function statusFonteUX(fonte) {
    if (fonte.coletaAutomatica === true) return ['Busca automática', 'automatico'];
    const s = String(fonte.status || '');
    if (s.includes('nao_usar_catalogo')) return ['Catálogo em verificação', 'validacao'];
    if (fonte.siteUrl) return ['Consultar site', 'manual'];
    return ['Site em verificação', 'validacao'];
  };

  state.tab = 'todos';
  const somente = document.querySelector('#somenteElegiveis');
  if (somente) somente.checked = false;
  const checkLabel = somente?.closest('label');
  if (checkLabel) {
    const texto = Array.from(checkLabel.childNodes).find(n => n.nodeType === Node.TEXT_NODE);
    if (texto) texto.textContent = ' Só com mínimos confirmados';
  }

  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('ativo', b.dataset.tab === 'todos'));
})();
