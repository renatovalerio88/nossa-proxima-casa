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

  function normalizarNome(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  function itemPertenceFonte(item, fonte) {
    const origem = normalizarNome(item?.fonte);
    const nomes = [fonte?.nome, ...(Array.isArray(fonte?.aliases) ? fonte.aliases : [])]
      .map(normalizarNome)
      .filter(Boolean);
    return nomes.some(nome => origem.includes(nome));
  }

  function coberturaFonte(fonte) {
    const relacionados = state.imoveis.filter(item => itemPertenceFonte(item, fonte));
    const ativos = relacionados.filter(item => typeof candidatoAtivo === 'function' ? candidatoAtivo(item) : ativo(item));
    const minimos = ativos.filter(item => item.elegibilidade?.elegivel === true).length;
    const confirmar = ativos.filter(item => item.elegibilidade?.status === 'pendente').length;
    const comFoto = ativos.filter(item => fotosConfiaveis(item).length > 0).length;
    return { relacionados: relacionados.length, ativos: ativos.length, minimos, confirmar, comFoto };
  }

  renderImobiliarias = function renderImobiliariasUX() {
    const lista = document.querySelector('#lista');
    lista.className = 'lista-fontes';
    const imobiliarias = state.fontes.filter(f => f.tipo === 'imobiliaria');
    if (!imobiliarias.length) {
      lista.innerHTML = '<div class="vazio"><strong>Nenhuma imobiliária carregada.</strong></div>';
      return;
    }

    const automaticas = imobiliarias.filter(f => f.coletaAutomatica === true).length;
    const comSite = imobiliarias.filter(f => Boolean(f.siteUrl)).length;
    const enriquecidas = imobiliarias.map(fonte => ({ fonte, cobertura: coberturaFonte(fonte) }));
    const comCandidato = enriquecidas.filter(x => x.cobertura.ativos > 0).length;
    const totalCandidatosVinculados = enriquecidas.reduce((s, x) => s + x.cobertura.ativos, 0);

    enriquecidas.sort((a, b) => {
      if (b.cobertura.ativos !== a.cobertura.ativos) return b.cobertura.ativos - a.cobertura.ativos;
      if (Boolean(b.fonte.siteUrl) !== Boolean(a.fonte.siteUrl)) return Number(Boolean(b.fonte.siteUrl)) - Number(Boolean(a.fonte.siteUrl));
      return a.fonte.nome.localeCompare(b.fonte.nome, 'pt-BR');
    });

    lista.innerHTML = `<div class="fontes-intro">
      <strong>${imobiliarias.length} imobiliárias no radar</strong>
      <span>${comSite} têm site identificado, mas apenas ${automaticas} permite coleta automática hoje. ${comCandidato} já têm candidatos ativos vinculados ao inventário${totalCandidatosVinculados ? ` (${totalCandidatosVinculados} vínculos)` : ''}. As demais continuam acessíveis para consulta direta, sem raspagem não autorizada.</span>
    </div>` + enriquecidas.map(({ fonte, cobertura }) => {
      const [status, tipo] = statusFonte(fonte);
      const link = fonte.siteUrl ? `<a href="${fonte.siteUrl}" target="_blank" rel="noopener noreferrer">Abrir site</a>` : '<span class="sem-link">Site oficial em verificação</span>';
      const coberturaTexto = cobertura.ativos > 0
        ? `${cobertura.ativos} candidato${cobertura.ativos === 1 ? '' : 's'} ativo${cobertura.ativos === 1 ? '' : 's'} · ${cobertura.minimos} mínimos OK${cobertura.comFoto ? ` · ${cobertura.comFoto} com foto` : ''}`
        : 'Nenhum candidato ativo vinculado ainda';
      const nota = fonte.coletaAutomatica === true
        ? 'Catálogo acompanhado automaticamente em baixa frequência.'
        : 'Consulta direta; candidatos só entram após verificação individual.';
      return `<article class="fonte-card">
        <div><strong>${fonte.nome}</strong><span class="fonte-status" data-tipo="${tipo}">${status}</span></div>
        <p class="fonte-cobertura">${coberturaTexto}</p>
        <p class="fonte-nota">${nota}</p>
        ${link}
      </article>`;
    }).join('');
  };

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
      partes.push(`${Number(status.imoveisComFotos)} anúncio${Number(status.imoveisComFotos) === 1 ? '' : 's'} com foto real na coleta atual`);
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