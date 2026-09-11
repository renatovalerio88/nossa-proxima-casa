(() => {
  const renderBase = render;

  function aplicarRotulos() {
    document.querySelectorAll('.qualidade[data-tipo="elegivel"]').forEach(el => {
      el.textContent = 'Mínimos OK';
      el.title = 'Cumpre os critérios mínimos confirmados. Isso não significa recomendação final.';
    });

    document.querySelectorAll('.match-pendente').forEach(el => {
      const texto = el.querySelector('span');
      if (texto) texto.textContent = 'Sem nota';
      el.title = 'O Match só aparece quando todos os componentes necessários estão disponíveis. Mínimos OK e Match são avaliações diferentes.';
      el.setAttribute('aria-label', 'Match ainda não calculável');
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
    const atualizado = dataPtBr(inv.atualizadoEm || status?.fim);
    const fontes = fontesData?.fontes || [];
    const imobiliarias = fontes.filter(f => f.tipo === 'imobiliaria').length;
    const partes = [];
    if (atualizado) partes.push(`Atualizado em ${atualizado}`);
    if (imobiliarias) partes.push(`${imobiliarias} imobiliárias monitoradas`);
    if (status && Number(status.imoveisComFotos || 0) > 0) {
      partes.push(`${Number(status.imoveisComFotos)} anúncios com foto real na coleta atual`);
    }
    return partes.length ? partes.join(' · ') : 'Radar atualizado';
  };

  statusFonte = function statusFonteUX(fonte) {
    if (fonte.coletaAutomatica === true) return ['Busca automática', 'automatico'];
    const s = String(fonte.status || '');
    if (s.includes('nao_usar_catalogo')) return ['Catálogo em verificação', 'validacao'];
    if (fonte.siteUrl) return ['Consultar site', 'manual'];
    return ['Site em verificação', 'validacao'];
  };

  // A home sempre abre no inventário útil. "Novos" continua disponível como filtro de revisão.
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
