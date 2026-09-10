(() => {
  const modal = document.querySelector('#galeriaModal');
  if (!modal) return;

  const imagem = modal.querySelector('.galeria-imagem');
  const contador = modal.querySelector('.galeria-contador');
  const legenda = modal.querySelector('.galeria-legenda');
  const anterior = modal.querySelector('.galeria-anterior');
  const proxima = modal.querySelector('.galeria-proxima');
  const fechar = modal.querySelector('.galeria-fechar');

  let fotos = [];
  let indice = 0;
  let titulo = '';
  let gatilho = null;

  function itemDaFoto(src) {
    if (typeof state === 'undefined' || !Array.isArray(state.imoveis) || typeof fotosConfiaveis !== 'function') return null;
    return state.imoveis.find(item => fotosConfiaveis(item).includes(src)) || null;
  }

  function atualizar() {
    if (!fotos.length) return;
    imagem.src = fotos[indice];
    imagem.alt = `${titulo || 'Foto real do imóvel'} — foto ${indice + 1} de ${fotos.length}`;
    contador.textContent = `${indice + 1} / ${fotos.length}`;
    legenda.textContent = titulo || 'Foto real do anúncio';
    anterior.hidden = fotos.length < 2;
    proxima.hidden = fotos.length < 2;
  }

  function abrir(wrap) {
    const img = wrap.querySelector('.foto');
    if (!img?.src) return;
    const item = itemDaFoto(img.src);
    const encontradas = item && typeof fotosConfiaveis === 'function' ? fotosConfiaveis(item) : [img.src];
    if (!encontradas.length) return;

    fotos = encontradas;
    indice = Math.max(0, fotos.indexOf(img.src));
    titulo = item?.titulo || (item?.bairro ? `Casa em ${item.bairro}` : 'Foto real do imóvel');
    gatilho = wrap;
    atualizar();
    modal.showModal();
    document.body.classList.add('galeria-aberta');
    fechar.focus();
  }

  function encerrar() {
    if (modal.open) modal.close();
  }

  function mover(delta) {
    if (fotos.length < 2) return;
    indice = (indice + delta + fotos.length) % fotos.length;
    atualizar();
  }

  function prepararWraps(root = document) {
    root.querySelectorAll?.('.foto-wrap:not([hidden])').forEach(wrap => {
      wrap.setAttribute('role', 'button');
      wrap.setAttribute('tabindex', '0');
      wrap.setAttribute('aria-label', wrap.dataset.galeria ? `Abrir galeria: ${wrap.dataset.galeria}` : 'Ampliar foto real do imóvel');
    });
  }

  document.addEventListener('click', event => {
    const wrap = event.target.closest?.('.foto-wrap:not([hidden])');
    if (wrap) abrir(wrap);
  });

  document.addEventListener('keydown', event => {
    const wrap = event.target.closest?.('.foto-wrap:not([hidden])');
    if (wrap && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      abrir(wrap);
      return;
    }
    if (!modal.open) return;
    if (event.key === 'ArrowLeft') mover(-1);
    if (event.key === 'ArrowRight') mover(1);
  });

  anterior.addEventListener('click', () => mover(-1));
  proxima.addEventListener('click', () => mover(1));
  fechar.addEventListener('click', encerrar);
  modal.addEventListener('click', event => {
    if (event.target === modal) encerrar();
  });
  modal.addEventListener('close', () => {
    document.body.classList.remove('galeria-aberta');
    imagem.removeAttribute('src');
    fotos = [];
    if (gatilho?.isConnected) gatilho.focus();
    gatilho = null;
  });

  new MutationObserver(() => prepararWraps()).observe(document.querySelector('#lista'), { childList: true, subtree: true });
  prepararWraps();
})();
