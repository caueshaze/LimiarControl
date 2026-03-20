export const landingStats = [
  {
    value: "01",
    label: "Painel central",
    description: "Campanha, ficha, inventario e board em uma experiencia conectada.",
  },
  {
    value: "RT",
    label: "Sync em tempo real",
    description: "Comandos, compras, rolagens e estados vivos entre mestre e jogadores.",
  },
  {
    value: "24/7",
    label: "Mesa persistente",
    description: "Sua campanha continua organizada entre uma sessao e outra.",
  },
  {
    value: "+",
    label: "Fluxo modular",
    description: "Comece pela ficha e expanda para catalogo, loja, NPCs e dashboard.",
  },
] as const;

export const landingFeatureCards = [
  {
    title: "Cockpit do mestre",
    description:
      "Notas, campanha, loja, NPCs e comandos ao vivo organizados como uma cabine de controle para a mesa.",
    accent: "from-limiar-500/30 via-limiar-400/10 to-transparent",
    iconPath:
      "M3.75 5.25A1.5 1.5 0 015.25 3.75h13.5a1.5 1.5 0 011.5 1.5v13.5a1.5 1.5 0 01-1.5 1.5H5.25a1.5 1.5 0 01-1.5-1.5V5.25zm4.5 2.25a.75.75 0 000 1.5h7.5a.75.75 0 000-1.5h-7.5zm0 4.5a.75.75 0 000 1.5h3.75a.75.75 0 000-1.5H8.25zm0 4.5a.75.75 0 000 1.5h6a.75.75 0 000-1.5h-6zm8.25-3.75a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm0 5.25a1.5 1.5 0 100-3 1.5 1.5 0 000 3z",
  },
  {
    title: "Sessao com presenca",
    description:
      "Board, ficha, acao do mestre e resposta imediata do grupo aparecem como uma experiencia unica.",
    accent: "from-sky-400/25 via-cyan-300/10 to-transparent",
    iconPath:
      "M4.5 6.75A2.25 2.25 0 016.75 4.5h10.5a2.25 2.25 0 012.25 2.25v6.75A2.25 2.25 0 0117.25 15H13.5l-3 3-3-3H6.75A2.25 2.25 0 014.5 13.5V6.75zm3.75 1.5a.75.75 0 000 1.5h7.5a.75.75 0 000-1.5h-7.5zm0 3.75a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-4.5z",
  },
  {
    title: "Inventario com contexto",
    description:
      "Itens de classe, compras da loja e recompensa do mestre se conectam ao mesmo universo visual e operacional.",
    accent: "from-emerald-400/25 via-emerald-300/10 to-transparent",
    iconPath:
      "M4.5 7.5A2.25 2.25 0 016.75 5.25h10.5A2.25 2.25 0 0119.5 7.5v9A2.25 2.25 0 0117.25 18.75H6.75A2.25 2.25 0 014.5 16.5v-9zm3 1.5a.75.75 0 000 1.5h9a.75.75 0 000-1.5h-9zm0 3.75a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5H7.5zM9 3.75a.75.75 0 000 1.5h6a.75.75 0 000-1.5H9z",
  },
  {
    title: "Rolagens com drama",
    description:
      "Feedback visual, status da rodada e leitura instantanea dos resultados ajudam a vender tensao e ritmo.",
    accent: "from-amber-400/25 via-rose-300/10 to-transparent",
    iconPath:
      "M11.25 3.75a2.25 2.25 0 011.5 0l5.25 1.875A2.25 2.25 0 0119.5 7.74v8.52a2.25 2.25 0 01-1.5 2.115l-5.25 1.875a2.25 2.25 0 01-1.5 0L6 18.375a2.25 2.25 0 01-1.5-2.115V7.74A2.25 2.25 0 016 5.625l5.25-1.875zm-2.25 4.5a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25zm6 1.125a1.125 1.125 0 11-2.25 0 1.125 1.125 0 012.25 0zm-3 4.5a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25z",
  },
] as const;

export const landingWorkflow = [
  {
    step: "01",
    title: "Monte a mesa",
    description:
      "Crie a campanha, organize NPCs, configure catalogo e deixe a sessao pronta antes do primeiro encontro.",
  },
  {
    step: "02",
    title: "Traga os jogadores",
    description:
      "Cada player entra no proprio fluxo: cria a ficha, escolhe equipamento inicial e acompanha o estado vivo da aventura.",
  },
  {
    step: "03",
    title: "Jogue ao vivo",
    description:
      "Loja, rolagens, comandos do mestre e inventario se mantem sincronizados sem trocar de ferramenta.",
  },
] as const;

export const landingSpotlights = [
  {
    title: "Fichas que nascem prontas para jogar",
    body: "Criacao guiada, equipamento inicial coerente e continuidade entre preparacao e campanha viva.",
  },
  {
    title: "Board e dashboard no mesmo idioma visual",
    body: "Menos friccao cognitiva entre o que o mestre organiza e o que o jogador enxerga em sessao.",
  },
  {
    title: "Arquitetura pensada para crescer",
    body: "Comece simples e encaixe novos modulos sem perder clareza nem previsibilidade de fluxo.",
  },
] as const;

export const landingEntryPoints = [
  {
    title: "Fluxo do jogador",
    body: "Entrar, montar ficha e seguir o pulso da sessao sem parecer que voce mudou de produto.",
    tone: "from-sky-400/24 via-sky-300/10 to-transparent",
  },
  {
    title: "Cockpit do mestre",
    body: "Campanha, inventario, comandos e modulos com a mesma atmosfera da primeira dobra da home.",
    tone: "from-limiar-500/24 via-limiar-300/10 to-transparent",
  },
  {
    title: "Entrada com clima",
    body: "Login e cadastro agora preparam melhor o usuario para a experiencia visual que vem depois.",
    tone: "from-amber-400/24 via-amber-300/10 to-transparent",
  },
] as const;
