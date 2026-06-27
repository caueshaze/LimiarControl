# Relatório Técnico — Linhagem Dracônica (D&D 5e) no Limiar

> Objetivo: servir de referência única para implementação fiel das regras dracônicas
> no motor do Limiar, contrastando o RAW (Rules As Written) com o estado atual do código
> e destacando armadilhas de implementação.
>
> Estado do código analisado: branch `wip/limiar-lab`, commit base `30b0d99`
> (*"Implement draconic resilience feature for sorcerer subclass"*).

---

## Sumário executivo — o que já existe no Limiar

| Característica | RAW | Implementado? | Onde |
|---|---|---|---|
| Dragonborn — Ancestralidade / tipo de dano / resistência | PHB 2014 | ✅ | `draconic_ancestry.py`, `dragonborn_ancestry.py` |
| Dragonborn — Arma de Sopro (dado, CD, forma, save) | PHB 2014 | ✅ | `dragonborn_breath_weapon.py`, `dragonbornBreathWeapon.ts` |
| Dragonborn — Resistência de dano em combate | PHB 2014 | ✅ | `damage_core.py` |
| Sorcerer — Draconic Resilience (HP +1/nível) | PHB 2014 | ✅ | `sorcerer_progression.py`, `class_progression.py` |
| Sorcerer — Draconic Resilience (CA 13 + Des) | PHB 2014 | ✅ | `session_state_finalize.py` |
| Sorcerer — Draconic Ancestry | PHB 2014 | ✅ | `sorcerer_progression.py` |
| Sorcerer — Elemental Affinity (resistência nível 6) | PHB 2014 | ✅ | `damage_core.py` |
| Sorcerer — Elemental Affinity (bônus de dano = Carisma) | PHB 2014 | ⚠️ **parcial** — calculado e exibido, **não somado** ao dano | `draconic_ancestry.py:resolve_elemental_affinity`, `SpellCastResultPanel.tsx` |
| Sorcerer — Dragon Wings (nível 14) | PHB 2014 | ❌ não implementado | — |
| Sorcerer — Draconic Presence (nível 18) | PHB 2014 | ❌ não implementado | — |
| Recarga da Arma de Sopro (descanso) | PHB 2014 | ⚠️ estrutura existe (`usesRemaining`), **reset por descanso não confirmado no fluxo** | `dragonborn_breath_weapon.py` |

**Convenção do código:** o módulo "canônico" é `draconic_ancestry.py`. `dragonborn_ancestry.py`
é uma camada fina que reexporta tudo, porque Dragonborn (raça) e Draconic Bloodline (subclasse)
compartilham **a mesma tabela de 10 ancestrais**. Há suporte a chaves legadas
(`dragonbornAncestry`, `dragonAncestor`) normalizadas para `draconicAncestry`.

---

## 1. Dragonborn (Raça)

### 1.1 Características — PHB 2014 (versão implementada)

| Traço | Valor |
|---|---|
| Aumento de atributo | +2 Força, +1 Carisma |
| Idade | adulto ~15 anos, vive ~80 anos |
| Tamanho | Médio (~1,8–2,1 m, >115 kg) |
| Deslocamento | 9 m (30 ft) |
| Idiomas | Comum, Dracônico |
| Ancestralidade Dracônica | escolha 1 dos 10 → define dano + resistência + sopro |
| Arma de Sopro | ação; dado escala por nível; 1 uso / descanso |
| Resistência a Dano | ao tipo de dano da ancestralidade |

### 1.2 Diferenças entre versões oficiais

| Aspecto | PHB 2014 (implementado) | Fizban's Treasury of Dragons (2021) | PHB 2024 |
|---|---|---|---|
| Aumentos de atributo | +2 FOR, +1 CAR fixos | flutuante (regra de Tasha's) | flutuante / Background |
| Subtipos | Cromático/Metálico misturados em 1 lista | **Cromático, Metálico, Gema** (3 famílias) | Cromático, Metálico, Gema |
| Arma de Sopro | 1 uso por descanso, dado escala 2d6→5d6 | uso = bônus de proficiência por descanso longo; pode usar no lugar de 1 ataque | igual Fizban's; vira **ação ou parte do Ataque** |
| Resistência | tipo da ancestralidade | idem | idem |
| Voo dracônico | — | **Draconic Flight** (feat, nível 5+): asas temporárias | mantido via feat |
| Gema (Gem dragons) | ausente | force/psychic/etc + sopro em **linha** | presente |
| Dano extra dracônico | — | feat *Gift of the Chromatic/Metallic/Gem Dragon* | embutido em alguns traços |

> **O Limiar implementa apenas o PHB 2014.** A tabela de ancestrais (10 entradas) **não inclui
> dragões-gema** e o número de usos do sopro é fixo em **1** (ver §1.5), ao contrário de Fizban's/2024
> que usam "proficiência por descanso".

### 1.3 Resistências

- Concede **resistência** (dano pela metade, arredondado para baixo) ao tipo de dano da ancestralidade.
- No Limiar: aplicada em [`damage_core.py`](../apps/control-server/app/services/combat_service/damage_core.py#L44-L59),
  via `_apply_player_damage_resistances` → `reduced = amount // 2`.
- A lista de resistências do Dragonborn vem de `resolve_dragonborn_lineage_state(...)["resistances"]`,
  que sempre retorna `[resistanceType]` quando há ancestralidade válida (resistência é **permanente**, do nível 1).

### 1.4 Arma de Sopro — RAW e implementação

| Parâmetro | Regra | Implementação Limiar |
|---|---|---|
| Ação | Ação | `actionId = "dragonborn_breath_weapon"` |
| Dado de dano | 2d6 (1º), 3d6 (6º²), 4d6 (11º), 5d6 (16º²) | **2d6 (<5), 3d6 (≥5), 4d6 (≥11), 5d6 (≥17)** ⚠️ ver nota |
| Tipo de dano | da ancestralidade | `lineage.damageType` |
| Forma | linha 1,5 m × 9 m **ou** cone 4,5 m | `breathWeaponShape`, `breathWeaponAreaSize` |
| Teste de resistência | Des (linha) ou Con (cone) | `breathWeaponSaveType` |
| CD | 8 + bônus proficiência + mod. **Constituição** | `compute_dragonborn_breath_weapon_dc` = `8 + prof + mod(CON)` ✅ |
| Sucesso no save | metade do dano | (a aplicar no resolvedor de área) |
| Usos | 1 / descanso (curto ou longo) | `usesMax = 1` fixo |

> ⚠️ **Armadilha — limiares de escalonamento do dado.** O PHB 2014 escala nos níveis
> **6/11/16**. O Limiar escala em **5/11/17** (ver `compute_dragonborn_breath_weapon_damage_dice`
> e `getDragonbornBreathWeaponDamageDice`). Isso é uma divergência consciente/erro a confirmar.
> Os dois lados (backend Python e frontend TS) estão **consistentes entre si**, então corrigir
> exige tocar nos dois.

### 1.5 Escalonamento e usos

- **Dado:** função pura de `level` (tabela acima). Backend e frontend duplicam a lógica — manter sincronizados.
- **Usos:** `compute_dragonborn_breath_weapon_uses_max()` retorna **sempre 1**, ignorando o nível.
  Em Fizban's/2024 seriam *proficiência* usos por descanso longo — **não implementado**.
- **Recarga:** o recurso `dragonbornBreathWeapon` carrega `usesRemaining`, mas a redução de
  `usesRemaining` no disparo e o **reset em descanso** dependem do fluxo de descanso/combate —
  **verificar `ensure_rest_state` / lógica de short/long rest** antes de afirmar que recarrega.

### 1.6 Casos especiais

- **Sopro + magia:** a Arma de Sopro **não** é magia; não conta como ataque de feitiço, não dispara
  contra-feitiço, não se beneficia de Elemental Affinity (que é da subclasse Sorcerer).
- **Save por metade:** alvos que passam tomam metade — precisa do mesmo resolvedor de área usado por
  magias de área (cone/linha) em `area_targeting.py`.
- **Multiataque/Ação Adicional:** PHB 2014 = Ação inteira. Em 2024 pode substituir 1 ataque do Attack action.

---

## 2. Sorcerer — Draconic Bloodline (PHB 2014)

Subclasse: `subclass = "draconic_bloodline"`. Config: `subclassConfig.draconicAncestry`
(legado `dragonAncestor` normalizado). Validação obrigatória em
`validate_draconic_subclass_state` — recusa criação sem ancestral válido.

### Nível 1 — Dragon Ancestor (Ancestral Dracônico)

| Campo | Detalhe |
|---|---|
| Habilidade | Escolha 1 dos 10 dragões → define **tipo de dano** da linhagem (usado por Elemental Affinity) |
| Efeito | Você fala Dracônico; **dobra o bônus de proficiência** em testes de Carisma ao interagir com dragões |
| Duração | Permanente |
| Limitação | A escolha é fixa na criação |
| Implementação | `build_sorcerer_class_features` → feature `draconic_ancestry` com `damageType`/`resistanceType` no metadata |
| ⚠️ Gap | O bônus social ("dobrar proficiência ao falar com dragões") **não** está modelado (é narrativo/GM) |

### Nível 1 — Draconic Resilience (Resiliência Dracônica)

| Campo | Detalhe |
|---|---|
| Efeito A | HP máximo **+1 por nível de Sorcerer** (retroativo e prospectivo) |
| Efeito B | Sem armadura, **CA base = 13 + mod. Destreza** |
| Duração | Permanente / passivo |
| Limitação | CA 13+Des só vale **sem armadura** (escudo é permitido e soma normalmente) |
| Implementação HP | `get_draconic_resilience_hit_point_bonus` = `level`; aplicado em `recompute_hit_points` / `apply_level_up_stats` (`_draconic_resilience_bonus_for_level`) |
| Implementação CA | `session_state_finalize.py:_build_player_armor_class_details` — candidato `source="draconic_resilience"`, `value = 13 + dex_mod`, `priority=35`, `applicable = is_draconic_bloodline_sorcerer` |
| Exemplo | Sorcerer 5, Des 14 (+2): CA sem armadura = **15**. HP = base d6 + 5. |

> **Detalhe de prioridade de CA:** `draconic_resilience` (35) > `barbarian_unarmored_defense` (30)
> > `monk_unarmored_defense` (20) > `default_unarmored`. Em **multiclasse** Sorcerer/Barbarian ou
> Sorcerer/Monk, o motor escolhe automaticamente a maior — e Draconic Resilience tende a vencer.
> Confirmar que isso é o desejado (RAW: jogador escolhe **qual** defesa sem armadura usar, não pode somar).

### Nível 6 — Elemental Affinity (Afinidade Elemental)

| Campo | Detalhe |
|---|---|
| Efeito A | Ao lançar magia de **dano do tipo da linhagem**, soma **mod. de Carisma** ao dano **uma vez** |
| Efeito B | Gastando 1 ponto de feitiçaria, ganha **resistência** a esse tipo de dano por **1 hora** |
| Duração | A: instantâneo (na magia); B: 1 hora |
| Limitação chave | O bônus é **uma vez por conjuração**, não por alvo nem por dado |
| Implementação resistência | `resolve_draconic_lineage_state`: `hasElementalAffinity = level>=6`; alimenta `resistances` em `damage_core.py` ✅ |
| Implementação bônus de dano | `resolve_elemental_affinity(data, spell_damage_type)` → `{eligible, damageType, bonus = mod(CAR)}`. Propagado por todo o pipeline de spells como `elemental_affinity_bonus` |
| ⚠️ **Gap crítico** | O bônus é **apenas exibido** ("bonus potencial +X" em `SpellCastResultPanel.tsx:154`) e **NÃO é somado ao total de dano automaticamente**. Aplicação fica a cargo do jogador/GM |

> **Duas divergências do RAW na resistência:**
> 1. RAW: a resistência **custa 1 ponto de feitiçaria** e **dura 1 hora**. No Limiar ela é tratada como
>    **permanente e gratuita** a partir do nível 6 (`hasElementalAffinity` → sempre na lista de resistências).
> 2. Isso simplifica, mas ignora o custo de recurso e a concorrência com outras magias.

> **Armadilha do "uma vez":** quando o bônus de dano for finalmente aplicado, ele deve entrar
> **uma única vez** no total — não por alvo de magia de área, não por dardo de Magic Missile, não por
> dado. O contexto já carrega `elemental_affinity_bonus` por alvo/efeito; ao somar, garantir
> de-duplicação por conjuração.

### Nível 14 — Dragon Wings (Asas de Dragão) — ❌ NÃO IMPLEMENTADO

| Campo | RAW |
|---|---|
| Efeito | Como ação bônus, brotam asas → **deslocamento de voo = deslocamento terrestre** |
| Duração | Até dispensar (ação bônus) ou ficar incapacitado |
| Limitação | Não funciona se houver **armadura média/pesada** sem espaço para asas |
| Implementação sugerida | efeito declarativo `modify_stat`(speed_fly) ativável por ação bônus; flag em estado de combate; checar conflito com armadura |

### Nível 18 — Draconic Presence (Presença Dracônica) — ❌ NÃO IMPLEMENTADO

| Campo | RAW |
|---|---|
| Efeito | Ação + 5 pontos de feitiçaria: aura 18 m → inimigos fazem save de Sabedoria ou ficam **amedrontados ou enfeitiçados** (escolha) |
| Duração | **Concentração**, até 1 minuto |
| Limitação | Save no início do turno de cada criatura para sair; quebra com dano/concentração |
| Implementação sugerida | efeito de área persistente com concentração; `apply_condition`(frightened/charmed); re-save por turno (padrão Compelled Duel já existe no motor) |

---

## 3. Tipos de Dragão (tabela de ancestrais)

Fonte da tabela: `DRACONIC_ANCESTRIES` em
[`draconic_ancestry.py`](../apps/control-server/app/services/draconic_ancestry.py#L7-L18).
Idêntica para Dragonborn (raça) e Draconic Bloodline (subclasse).

| Ancestral | Tipo de dano | Resistência | Forma do sopro | Área | Teste |
|---|---|---|---|---|---|
| Black (Negro) | acid | acid | linha | 1,5 m × 9 m | Destreza |
| Blue (Azul) | lightning | lightning | linha | 1,5 m × 9 m | Destreza |
| Brass (Latão) | fire | fire | linha | 1,5 m × 9 m | Destreza |
| Bronze | lightning | lightning | linha | 1,5 m × 9 m | Destreza |
| Copper (Cobre) | acid | acid | linha | 1,5 m × 9 m | Destreza |
| Gold (Ouro) | fire | fire | cone | 4,5 m | Constituição |
| Green (Verde) | poison | poison | cone | 4,5 m | Constituição |
| Red (Vermelho) | fire | fire | cone | 4,5 m | Constituição |
| Silver (Prata) | cold | cold | cone | 4,5 m | Constituição |
| White (Branco) | cold | cold | cone | 4,5 m | Constituição |

Padrão RAW confirmado: **linha → save de Destreza**; **cone → save de Constituição**.
Dragões-gema (force, psychic, etc.) **não existem** nesta tabela (só viriam de Fizban's/2024).

---

## 4. Implementação — anatomia de cada característica

### 4.1 Modelo de dados (persistência)

- **Dragonborn:** `data.race = "dragonborn"`, `data.raceConfig.draconicAncestry`.
- **Sorcerer:** `data.class = "sorcerer"`, `data.subclass = "draconic_bloodline"`,
  `data.subclassConfig.draconicAncestry`.
- **Estado derivado canônico:** recalculado em `apply_sorcerer_canonical_state`,
  `apply_dragonborn_breath_weapon_canonical_state` e `finalize_session_state_data`.
  `classFeatures` é **regenerado** a cada finalize (fonte da verdade = função pura, não persistida solta).

### 4.2 Por característica

| Característica | Dispara quando | Eventos | Atributos afetados | Mod. permanente | Mod. temporário | Recursos | Cooldown | Persistência |
|---|---|---|---|---|---|---|---|---|
| Resistência Dragonborn | recebe dano do tipo | resolução de dano | HP recebido | dano ÷2 ao tipo | — | — | — | derivado de `raceConfig` |
| Arma de Sopro | jogador usa ação | ação de combate | HP dos alvos | — | — | `dragonbornBreathWeapon.usesRemaining` | 1/descanso | recurso em `classResources` |
| Draconic Resilience (HP) | recompute/level-up | finalize, level-up | `maxHP`, `currentHP` | +1/nível Sorcerer | — | — | — | em `maxHpBreakdown` |
| Draconic Resilience (CA) | finalize (sem armadura) | recálculo de CA | `armorClass` | CA=13+Des se desarmado | — | — | — | `armorClassSource` |
| Draconic Ancestry | criação/finalize | build features | tipo de dano lógico | define `damageType` | — | — | — | `subclassConfig` |
| Elemental Affinity (resist.) | recebe dano do tipo, nível ≥6 | resolução de dano | HP recebido | dano ÷2 (atualmente permanente) | (RAW: 1h, custa ponto) | (RAW: 1 ponto feitiçaria) | — | derivado |
| Elemental Affinity (dano) | conjura magia do tipo | pipeline de spell | dano da magia | — | +mod(CAR) **uma vez** | — | — | só exibido; **não somado** |
| Dragon Wings | ❌ | — | deslocamento de voo | — | speed_fly = speed | (sem custo) | — | a fazer |
| Draconic Presence | ❌ | — | condição em inimigos | — | frightened/charmed | 5 pontos feitiçaria | concentração 1min | a fazer |

---

## 5. Casos de borda

1. **Multiclasse Dragonborn + Sorcerer Draconic.** Raça e subclasse usam a **mesma tabela**.
   Se o tipo de dano coincidir (ex.: Dragonborn vermelho + linhagem vermelha = fogo), a resistência
   **não empilha** — `damage_core` usa um **set** de tipos (`resistances = {...}`), então é dedup
   automaticamente. ✅ (resistência não é cumulativa por RAW: resistência aplicada **uma vez**).

2. **Multiclasse e CA sem armadura.** Sorcerer/Barbarian/Monk: o motor escolhe a maior fórmula por
   prioridade (35/30/20). RAW permite ao jogador **escolher uma**, não somar — comportamento atual ok,
   mas é automático (não dá escolha ao jogador). Conferir se há intenção de UI de escolha.

3. **Wild Shape (Druida/multiclasse).** Em `finalize_session_state_data`, se `wildShape.active`, a CA
   passa a ser a da **forma da fera** (ignora Draconic Resilience). RAW: traços raciais como resistência
   **continuam**; traços de classe que dependem de mãos/voz não. ⚠️ Verificar se a **resistência
   dracônica** e o **HP +1/nível** persistem corretamente durante Wild Shape (HP da fera substitui o do
   personagem; ao voltar, HP original — `recompute_hit_points` deve restaurar com `preserve_damage`).

4. **Efeitos que alteram tipo de dano** (ex.: metamagia, *Elemental Adept*, transmutação de dano).
   Elemental Affinity casa pelo **tipo de dano final da magia** (`spell_damage_type`). Se o tipo for
   alterado **após** o cálculo de afinidade, o `eligible` pode ficar incorreto. Garantir que
   `resolve_elemental_affinity` rode com o **tipo já transformado**.

5. **Resistências duplicadas / imunidade.** O motor só modela **resistência** (÷2). Não há canal para
   **imunidade** dracônica nem para "vulnerabilidade". Se o alvo tiver resistência por outra fonte +
   dracônica, RAW **não** dobra (continua ÷2). O set já garante isso para fontes dracônicas; conferir
   interação com resistências de NPC/efeitos (Warding Bond é tratado **separadamente** em
   `_apply_warding_bond_resistance`, aplicado em sequência — pode encadear ÷2 duas vezes, o que é
   correto para fontes independentes).

6. **Concentração.** Draconic Presence (não implementada) usa concentração — ao implementar, integrar
   com o sistema de concentração existente (quebra por dano, troca de magia). Elemental Affinity e
   Resilience **não** usam concentração.

7. **Ataques mágicos vs não mágicos.** A Arma de Sopro **não é mágica**: não supera resistência a
   "dano não-mágico", não dispara *Counterspell*, não recebe Elemental Affinity. O dano de magia do
   Sorcerer **é** mágico. Manter essa distinção ao calcular resistências do alvo (ex.: alvo com
   "resistência a dano não-mágico" **não** reduz a magia, mas reduz dano físico).

8. **Save por metade no sopro.** Tanto linha quanto cone causam **metade do dano** em save bem-sucedido
   — usar o mesmo resolvedor de área das magias (`area_targeting.py`) e **não** "nada em sucesso".

9. **Escalonamento divergente do sopro (5/11/17 vs 6/11/16 RAW).** Ver §1.4 — afeta níveis 5, 6, 16 e 17.

10. **Reset de usos do sopro.** Confirmar que `usesRemaining` volta a `usesMax` em descanso curto **e**
    longo (RAW PHB 2014: "after a rest"). Se o fluxo de descanso não restaurar `classResources`, o sopro
    fica gasto para sempre — bug latente a verificar.

---

## 6. Referências

| Regra | Origem oficial |
|---|---|
| Dragonborn (raça), +2 FOR/+1 CAR, sopro 2d6→5d6 em 6/11/16, 1 uso/descanso | **Player's Handbook 2014**, cap. 2 "Races" |
| Tabela Draconic Ancestry (10 dragões, dano/save/forma) | **PHB 2014**, "Draconic Ancestry" |
| Sorcerer — Draconic Bloodline (níveis 1/6/14/18) | **PHB 2014**, cap. 3 "Sorcerer" |
| Atributos flutuantes (alternativa) | **Tasha's Cauldron of Everything (2020)** |
| Subtipos Cromático/Metálico/**Gema**, sopro = proficiência/descanso, Draconic Flight feat, dragões-gema | **Fizban's Treasury of Dragons (2021)** |
| Dragonborn revisado, sopro como ação **ou** parte do Ataque, atributos no Background | **Player's Handbook 2024** |
| Elemental Affinity: bônus de dano **uma vez por conjuração** | **Sage Advice** / PHB 2014 ("when you cast a spell") |
| Resistência não empilha (aplicada uma vez) | **PHB 2014**, "Damage Resistance and Vulnerability" |

### Notas de versão (não misturar)

- **O Limiar segue PHB 2014.** Não combinar com sopro de Fizban's (proficiência/descanso) nem com
  dragões-gema sem decisão explícita de produto.
- Se for migrar para Fizban's/2024: mudar `compute_dragonborn_breath_weapon_uses_max` (→ proficiência),
  permitir sopro como parte do Ataque, e estender `DRACONIC_ANCESTRIES` com famílias gema (force/psychic).

---

## Apêndice — Pendências de implementação priorizadas

1. **[Bug provável]** Corrigir escalonamento do dado de sopro para **6/11/16** (backend + frontend) — §1.4.
2. **[Gap funcional]** Somar de fato o `elemental_affinity_bonus` ao dano (uma vez por conjuração),
   não apenas exibir — §2 nível 6.
3. **[Divergência RAW]** Decidir se a resistência de Elemental Affinity deve custar ponto de feitiçaria
   e durar 1h (RAW) em vez de permanente/gratuita — §2 nível 6.
4. **[Verificar]** Reset de `dragonbornBreathWeapon.usesRemaining` em descanso — §1.5 / §5.10.
5. **[Feature]** Implementar Dragon Wings (nível 14) e Draconic Presence (nível 18) — §2.
6. **[Verificar]** Persistência de resistência/HP dracônicos durante Wild Shape — §5.3.
