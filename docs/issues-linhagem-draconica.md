# Issues — Linhagem Dracônica (Dragonborn + Sorcerer Draconic Bloodline)

Derivadas de [relatório-linhagem-draconica.md](relatório-linhagem-draconica.md).
Cada issue é independente, mas **issues 1–3 são bugs/gaps críticos**; **4–5 são features**; **6–7 são validações**.

---

## Issue 1: Corrigir escalonamento do Dragonborn Breath Weapon (5/11/17 → 6/11/16)

**Tipo:** Bug — divergência do RAW  
**Prioridade:** Alta  
**Status:** Pendente

### Descrição do problema

O Dragonborn Breath Weapon escala o dado em limiares **incorretos**:

| Nível | Implementado | RAW (PHB 2014) | Divergência |
|---|---|---|---|
| 1–4 | 2d6 | 2d6 | ✅ correto |
| 5–10 | **3d6** ⚠️ | 2d6 | ❌ corre em nível 5, deveria ser 6 |
| 11–15 | 4d6 | 4d6 | ✅ correto |
| 16–17 | **5d6** ⚠️ | 4d6 (16), 5d6 (17) | ❌ avança em nível 17, deveria ser 16 |

Afeta Dragonborn níveis 5–6 (cedo demais) e níveis 16–17 (um nível tarde).

### Regra esperada

PHB 2014, Dragonborn Ancestry, Breath Weapon:
> "Você pode usar sua ação para exalar destruição nesse formato. Cada criatura nessa área deve fazer 
> um teste de resistência. [...] 1º nível: 2d6. 6º nível: 3d6. 11º nível: 4d6. 16º nível: 5d6."

### Arquivos envolvidos

**Backend:**
- [`apps/control-server/app/services/dragonborn_breath_weapon.py:29–37`](../apps/control-server/app/services/dragonborn_breath_weapon.py#L29-L37)
  ```python
  def compute_dragonborn_breath_weapon_damage_dice(level: int) -> str:
      if normalized_level >= 17: return "5d6"  # ← deveria ser >= 16
      if normalized_level >= 11: return "4d6"
      if normalized_level >= 5: return "3d6"   # ← deveria ser >= 6
      return "2d6"
  ```

**Frontend:**
- [`apps/control-web/src/features/character-sheet/data/dragonbornAncestries.ts:74–80`](../apps/control-web/src/features/character-sheet/data/dragonbornAncestries.ts#L74-L80)
  ```typescript
  if (normalizedLevel >= 17) return "5d6";    // ← deveria ser >= 16
  if (normalizedLevel >= 11) return "4d6";
  if (normalizedLevel >= 5) return "3d6";     // ← deveria ser >= 6
  ```

### Risco estimado

**Baixo.** Mudança de constante pura; sem quebra de contrato de API, sem efeitos colaterais.
Testes redundam — a função é determinística.

### Critérios de aceite

- [ ] Backend: `compute_dragonborn_breath_weapon_damage_dice` usa 6, 11, 16 (não 5, 11, 17)
- [ ] Frontend: `getDragonbornBreathWeaponDamageDice` sincronizado com backend
- [ ] Dragonborn nível 5: continua 2d6
- [ ] Dragonborn nível 6: agora 3d6 (em vez de 3d6, mas timing correto)
- [ ] Dragonborn nível 16: agora 5d6 (em vez de 4d6)
- [ ] Dragonborn nível 17: continua 5d6

### Testes necessários

- [ ] Teste unitário backend: `test_dragonborn_breath_weapon_damage_dice(level=5)` → "2d6"
- [ ] Teste unitário backend: `test_dragonborn_breath_weapon_damage_dice(level=6)` → "3d6"
- [ ] Teste unitário backend: `test_dragonborn_breath_weapon_damage_dice(level=16)` → "5d6"
- [ ] Teste unitário frontend: `getDragonbornBreathWeaponDamageDice(5)` → "2d6"
- [ ] Teste unitário frontend: `getDragonbornBreathWeaponDamageDice(6)` → "3d6"
- [ ] Teste de caractere: criar Dragonborn níveis 6 e 16, verificar dado exibido em "Dragonborn Breath Weapon"

---

## Issue 2: Implementar Elemental Affinity — soma do modificador de Carisma ao dano

**Tipo:** Gap funcional — bônus exibido mas não aplicado  
**Prioridade:** Alta (afeta gameplay)  
**Status:** Pendente

### Descrição do problema

Sorcerer Draconic Bloodline nível 6+ ganha **Elemental Affinity**: soma do modificador de Carisma 
ao dano de magias do tipo de dano da linhagem, **uma vez por conjuração**.

**Estado atual:**
- ✅ `resolve_elemental_affinity` calcula o bônus (`mod(CAR)`)
- ✅ é propagado como `elemental_affinity_bonus` pelo pipeline de spells
- ✅ é **exibido** em `SpellCastResultPanel.tsx:154` como "bonus potencial"
- ❌ **não é somado** ao total de dano aplicado ao alvo

**Resultado:** o bônus é mostrado, mas o alvo não recebe o dano adicional.

### Regra esperada

PHB 2014, Sorcerer — Elemental Affinity (nível 6):
> "Quando você conjura uma magia de feiticeiro que causa dano do tipo associado a sua linhagem dracônica,
> você pode adicionar seu modificador de Carisma ao dano dessa magia."

Notas:
- Aplica-se **ao dano da magia, uma vez** (não por alvo, não por dado de dano).
- Exemplo: *Fireball* (10d6 fogo, 5 alvos) recebe +CHA **uma única vez no total**, não 5×CHA.
- Magic Missile (múltiplos dardos): +CHA uma vez, distribuído entre os dardos ou no primeiro?
  (frequentemente interpretado como "uma vez por conjuração", não especificado qual dardo).

### Arquivos envolvidos

**Cálculo (já existe):**
- [`apps/control-server/app/services/draconic_ancestry.py:137–159`](../apps/control-server/app/services/draconic_ancestry.py#L137-L159)
  — `resolve_elemental_affinity(data, spell_damage_type)` retorna `{eligible, bonus}`

**Pipeline de propagação (já existe):**
- [`apps/control-server/app/services/combat_service/spells/spell_context_resolve.py:954–1208`](../apps/control-server/app/services/combat_service/spells/spell_context_resolve.py#L954-L1208)
  — `_resolve_upcast_and_affinity` popula `elemental_affinity_bonus`

**Aplicação (precisa implementar):**
- [`apps/control-server/app/services/combat_service/spells/cast_target_effect.py`](../apps/control-server/app/services/combat_service/spells/cast_target_effect.py)
  — método que soma dano a alvos; precisa consultar `pending_spell.elemental_affinity_bonus`
- [`apps/control-server/app/services/combat_service/spells/cast_area_effect.py`](../apps/control-server/app/services/combat_service/spells/cast_area_effect.py)
  — idem para magias de área (atenção: somar **uma vez**, não por alvo)
- [`apps/control-server/app/services/combat_service/damage_core.py`](../apps/control-server/app/services/combat_service/damage_core.py)
  — possível hook centralizado para aplicar bônus

**Exibição (já existe):**
- [`apps/control-web/src/pages/PlayerBoardPage/player-combat-debug/SpellCastResultPanel.tsx:152–154`](../apps/control-web/src/pages/PlayerBoardPage/player-combat-debug/SpellCastResultPanel.tsx#L152-L154)

### Risco estimado

**Médio.** A aplicação do bônus toca o pipeline de dano; erros podem multiplicar o bônus 
(por alvo, por dado, etc.). Requer testes abrangentes.

Risco de regressão em magias de área existentes (Fireball, Cone of Cold, etc.) — garantir que 
bônus **não** é aplicado a tipos de dano que não coincidem ou a casters que não são Draconic Sorcerers.

### Critérios de aceite

- [ ] Sorcerer Draconic 6+, lança magia de dano tipo X (= linhagem), recebe +mod(CAR) no total de dano
- [ ] Bônus é aplicado **uma única vez** por conjuração (Magic Missile: +CHA repartido ou no primeiro dardo?)
- [ ] Magias de área (Fireball): +CHA **uma vez**, **não** por alvo
- [ ] Bônus só é aplicado se `elemental_affinity_eligible == true`
- [ ] Bônus é **zero** se nível < 6 ou se tipo de dano não coincide
- [ ] Não há empilhamento: Elemental Affinity + Elemental Adept (feat) = 1×CHA + 1d4 extra, não 2×CHA
- [ ] Exibição em SpellCastResultPanel continua mostrando "bonus potencial" (para auditoria)

### Testes necessários

**Unitários:**
- [ ] `resolve_elemental_affinity(sorcerer_lvl6_red_draconic, "fire")` → `{eligible: true, bonus: +3}`
- [ ] `resolve_elemental_affinity(sorcerer_lvl6_red_draconic, "cold")` → `{eligible: false, bonus: None}`
- [ ] `resolve_elemental_affinity(sorcerer_lvl5_red_draconic, "fire")` → `{eligible: false, bonus: None}` (nível insuficiente)

**Integração:**
- [ ] Sorcerer Draconic Vermelha nível 6, CAR 16 (+3):
  - Conjura *Fire Bolt* (1d10 fogo) contra inimigo AC 12: resultado deve ser dano = 1d10 + 3 (não 1d10)
  - Registrar no SpellCastResultPanel
- [ ] Sorcerer Draconic Azul nível 6, CAR 14 (+2):
  - Conjura *Fireball* (10d6 fogo) contra 5 alvos AC 13: total de dano = 10d6 + 2 (uma vez, não 5×)
  - Verificar que cada alvo que falha recebe esse total
- [ ] Sorcerer Draconic Verde nível 6, CAR 10 (mod 0):
  - Conjura *Poison Spray* (veneno): dano = esperado (0 de bônus)
- [ ] Wizard (não é Sorcerer Draconic) conjura *Fire Bolt*: nenhum bônus

---

## Issue 3: Revisar Elemental Affinity Resistance (RAW compliance)

**Tipo:** Divergência do RAW  
**Prioridade:** Alta (regra de recurso importante)  
**Status:** Pendente

### Descrição do problema

Nível 6 — Elemental Affinity concede **resistência** ao tipo de dano da linhagem.

**RAW (PHB 2014):**
> "Quando você conjura uma magia de feiticeiro que causa dano do tipo associado a sua linhagem dracônica,
> você pode adicionar seu modificador de Carisma ao dano dessa magia. **Você também pode gastar 1 ponto de 
> feitiçaria para ganhar resistência a esse tipo de dano pelo próximo minuto.**"

**Estado atual no Limiar:**
- Resistência é **permanente** (sempre ativa a partir do nível 6)
- Resistência é **gratuita** (não custa ponto de feitiçaria)
- Resistência não tem **duração** (não expira)

### Regra esperada

- Resistência é uma **ação livre** que custa **1 ponto de feitiçaria**
- Dura **1 minuto** (10 rodadas de combate)
- Ativa a pedido do jogador (não permanente)
- Pode ser gastada múltiplas vezes (se houver pontos)

### Arquivos envolvidos

**Onde a resistência é alimentada:**
- [`apps/control-server/app/services/draconic_ancestry.py:102–134`](../apps/control-server/app/services/draconic_ancestry.py#L102-L134)
  — `resolve_draconic_lineage_state`: `hasElementalAffinity = level >= 6`
  — popula `resistances = [resistanceType]`

**Onde é aplicada:**
- [`apps/control-server/app/services/combat_service/damage_core.py:44–59`](../apps/control-server/app/services/combat_service/damage_core.py#L44-L59)
  — `_apply_player_damage_resistances` verifica `resistances`

**Onde o efeito deveria ser**
- Modelo: usar sistema de efeitos persistentes (`persisted_effects` ou `active_effects`)
  — já existe em `session_state_finalize.py:prune_expired_persisted_effects_from_state`
- Triggering: ação de combate (ex.: similar a "Draconic Presence" não implementado)
- Duração: escalonada por tempo de jogo (`game_time_seconds`)

### Risco estimado

**Médio-Alto.** Requer redesenho da representação de resistência: sair de `resolve_draconic_lineage_state` 
(permanente) para `persisted_effects` (temporário). Pode afetar UI de status (como renderizar "resistência temporária"?).

Risco de regressão: se a resistência sair de `lineage_state`, pode quebrar código que assume resistência 
permanente (verificar `damage_core`).

### Critérios de aceite

- [ ] Elemental Affinity (nível 6+) **não** concede resistência automaticamente
- [ ] Jogador pode gastar 1 ponto de feitiçaria para ativar resistência por 1 minuto
- [ ] Resistência expira após 1 minuto (10 rodadas)
- [ ] Pode ser ativada múltiplas vezes (múltiplas vezes em combate, cada uma custa 1 ponto)
- [ ] Indicador de status mostra "resistência elemental ativa" + tempo restante
- [ ] Se o Sorcerer ficar incapacitado, resistência **não** é quebrada (concentração não é necessária)
- [ ] Ao sair de combate, a resistência expira (ou ser mantida para OOC? decisão de design)

### Testes necessários

**Unitários:**
- [ ] Sorcerer nível 6 com resistência **inativa** a fogo: recebe dano normalmente
- [ ] Gasta 1 ponto (sorcery point): efeito `type=resistance, damageType=fire, expiresAt=now+60s` criado
- [ ] Sorcerer nível 6 com resistência **ativa** a fogo: recebe metade do dano de fogo
- [ ] Após 1 minuto, resistência expira: dano volta ao normal
- [ ] Sorcerer com 1 ponto total tenta usar 2× resistência: primeira funciona, segunda falha (insuficiente recurso)

**Integração:**
- [ ] Combate: Sorcerer Dracônico Azul nível 6, recebe *Lightning Bolt* (60 dano):
  - Sem resistência: recebe 60
  - Gasta 1 ponto, ativa: recebe 30 (metade)
  - Tempo avança 61 segundos: resistência expira, próximo dano é 60 novamente
- [ ] UI: mostrar ícone/badge de "Resistência temporária — 30s" em character status

---

## Issue 4: Implementar Dragon Wings (Draconic Bloodline, nível 14)

**Tipo:** Feature faltante  
**Prioridade:** Média (é um nível alto, menos impacto imediato)  
**Status:** Pendente

### Descrição do problema

Sorcerer Draconic nível 14 ganha **Dragon Wings** — asas de dragão temporárias que concedem voo.

**Estado atual:** não existe no código (grep não retorna nada).

### Regra esperada

PHB 2014, Sorcerer — Dragon Wings (nível 14):
> "A partir de 14º nível, você pode usar uma ação bônus para fazer crescer asas dracônicas de fogo astral.
> Você ganha uma velocidade de voo igual à sua velocidade de caminhada. As asas duram até você dispensá-las 
> como uma ação bônus. Você não pode manifestar as asas se estiver usando armadura de cota de malha ou mais pesada,
> nem se estiver usando armadura que não tenha sido criada para abrigar asas."

**Interpretação:**
- Ação bônus para ativar (ação bônus para desativar)
- Velocidade de voo = velocidade terrestre do personagem
- **Restrição:** não pode voo em armadura média/pesada (regra RAW, mas em muitas mesas é ignorada — 
  conferir intenção de design do Limiar)
- **Duração:** até dispensar (ação bônus)
- **Não é mágica vinculada a concentração** (nada o quebra além de ação bônus)

### Arquivos envolvidos

**Sistema de efeitos:**
- [`apps/control-server/app/services/sorcerer_progression.py`](../apps/control-server/app/services/sorcerer_progression.py)
  — adicionar feature ao `build_sorcerer_class_features` (nível 14)
- Modelo: usar `persisted_effects` (similar a Draconic Presence) ou flag direto em `speed_fly`

**Ações de combate:**
- [`apps/control-server/app/services/combat_service/player_actions.py`](../apps/control-server/app/services/combat_service/player_actions.py)
  — implementar ação bônus "Ativar/desativar asas"

**Cálculo de velocidade:**
- [`apps/control-server/app/services/session_state_finalize.py`](../apps/control-server/app/services/session_state_finalize.py)
  — ao finalizar, se asas ativas, `speed_fly = speed_walk`

**Restrição de armadura (opcional):**
- Verificar `has_equipped_armor()` se quiser forçar RAW

### Risco estimado

**Baixo-Médio.** Feature isolada, sem interações complexas. Risco: se ações bônus tiverem bugs, 
toggle de asas pode ficar travado (sempre ligado/desligado).

### Critérios de aceite

- [ ] Sorcerer Draconic nível 14: ação bônus "Dragon Wings — Ativar" disponível
- [ ] Ao ativar: velocidade de voo = velocidade de caminhada
- [ ] Ação bônus "Dragon Wings — Desativar" torna-se disponível (e primeira ação desaparece)
- [ ] Ao desativar: velocidade de voo volta a zero
- [ ] Fora de combate: asas persistem entre rodadas (até ação bônus desativar)
- [ ] *(Opcional)* Rejeitar ativação se em armadura média/pesada (regra RAW)
- [ ] UI: mostrar "Asas de dragão — ativas" em status de combate

### Testes necessários

**Unitários:**
- [ ] Sorcerer nível 14 com `dragon_wings` effect: `speed_fly = speed_walk`
- [ ] Sorcerer nível 13: nenhum effect criado
- [ ] Sorcerer nível 14 com dragon_wings ativo, depois dispensa: `speed_fly = 0`

**Integração:**
- [ ] Combate: Sorcerer nível 14, Des 16 (speed 30):
  - Rodada 1: ação bônus "Dragon Wings Ativar" → `speed_fly = 30` (4,5 m em 6 segundos combate)
  - Rodada 2: move-se 20 ft no chão, depois 30 ft no ar
  - Rodada 3: ação bônus "Dragon Wings Desativar" → `speed_fly = 0`
  - Próxima rodada: só movimento terrestre
- [ ] *(Se RAW)* Com armadura de cota de malha: tenta ativar asas → erro "não pode com armadura"

---

## Issue 5: Implementar Draconic Presence (Draconic Bloodline, nível 18)

**Tipo:** Feature faltante  
**Prioridade:** Média (nível bem alto, afeta dinâmica de combate)  
**Status:** Pendente

### Descrição do problema

Sorcerer Draconic nível 18 ganha **Draconic Presence** — aura de pavor/encantamento.

**Estado atual:** não existe no código.

### Regra esperada

PHB 2014, Sorcerer — Draconic Presence (nível 18):
> "A partir de 18º nível, você pode canalizando a magia dracônica, você pode escolher quantas criaturas 
> que consiga ver a até 18 metros de você que você possa ver. Cada criatura deve fazer um teste de 
> resistência de Sabedoria. [...] No início do seu turno, você pode gastar 1 ponto de feitiçaria e 
> repetir esse efeito, requerendo um novo teste de resistência. Uma criatura com sucesso no teste 
> fica imune a este efeito por 24 horas."

Variante mais comum nas mesas (e frequentemente adotada por SRD online):
> "Como uma ação, você pode gastar 5 pontos de feitiçaria para exalar uma aura de energia dracônica 
> até 18 metros de distância por um minuto. Criaturas inimigas nessa área devem fazer um save de 
> Sabedoria ou ficam amedrontadas ou enfeitiçadas (escolha sua linhagem)."

**Interpretação (segunda):**
- **Ação** (não bônus)
- **5 pontos de feitiçaria** (alto custo)
- **Concentração** até 1 minuto
- **Raio:** 18 metros (9 quadrados)
- **Save:** Sabedoria
- **Efeito:** escolher **Assustado** (frightened) ou **Enfeitiçado** (charmed), aplicar a todos
- **Dinâmica:** no início do turno de cada criatura, pode repetir save para sair (padrão condições)

### Arquivos envolvidos

**Sistema de efeitos/condições:**
- [`apps/control-server/app/schemas/combat_spells.py`](../apps/control-server/app/schemas/combat_spells.py)
  — definir efeito `draconic_presence`
- [`apps/control-server/app/services/sorcerer_progression.py`](../apps/control-server/app/services/sorcerer_progression.py)
  — adicionar feature (nível 18)

**Ação em combate:**
- [`apps/control-server/app/services/combat_service/player_actions.py`](../apps/control-server/app/services/combat_service/player_actions.py)
  — implementar ação "Draconic Presence"

**Aplicação de efeito:**
- [`apps/control-server/app/services/combat_service/spells/cast_area.py`](../apps/control-server/app/services/combat_service/spells/cast_area.py)
  (ou equivalente para ações não-feitiço) — aplicar `apply_condition(frighte|charmed)` com concentração
- Precedente: `Compelled Duel` já implementa save por turno + concentração

**Recurso:**
- Gastar 5 pontos de feitiçaria (validar `sorceryPoints.current >= 5`)

### Risco estimado

**Médio-Alto.** Requer integração com:
- Sistema de concentração (pode quebrar outro efeito)
- Sistema de áreas e saves (uso padrão)
- Condições persistentes (padrão existente)

Risco de regressão em concentração: se houver bug na fila de concentração, pode impedir ativar.

### Critérios de aceite

- [ ] Sorcerer nível 18, 5+ sorcery points: ação "Draconic Presence" disponível
- [ ] Ao usar: escolhe "Assustado" ou "Enfeitiçado"
- [ ] Todas as criaturas inimigas a até 18 m fazem save de Sabedoria
- [ ] Falha: recebem condição escolhida por 1 minuto (concentração)
- [ ] Sucesso: imune (nada acontece)
- [ ] No início do turno de cada criatura afetada: pode repetir save para sair
- [ ] Se o Sorcerer perde concentração: todas as condições removidas
- [ ] Se concentração é quebrada por dano: testa concentração (padrão)
- [ ] UI: mostra "Draconic Presence — X criaturas afetadas, Y tempo restante"
- [ ] Save falho → "Assustado por Draconic Presence — save no início do turno"

### Testes necessários

**Unitários:**
- [ ] `resolve_draconic_presence_effect(sorcerer_lvl18, "frightened")` → `{type: "condition", condition: "frightened", duration: 60s}`
- [ ] `resolve_draconic_presence_effect(sorcerer_lvl17)` → `null` (nível insuficiente)
- [ ] Verificar que concentração é registrada

**Integração:**
- [ ] Combate: Sorcerer nível 18, 5 pontos, 3 inimigos a 10 m
  - Usa ação "Draconic Presence (Assustado)"
  - Inimigo 1 save de SAB: falha → fica assustado
  - Inimigo 2 save de SAB: sucesso → nada
  - Inimigo 3 save de SAB: falha → fica assustado
  - Status: "Draconic Presence ativa — 2 assustados, 59s restantes"
  - Próximo turno do Inimigo 1: pode fazer save de SAB para sair (padrão)
- [ ] Concentração quebrada (toma dano, falha no teste): Draconic Presence encerra, condições removidas
- [ ] UI: mostrar "Assustado — Draconic Presence" (origem do medo)
- [ ] Sem 5 pontos: ação desabilitada (cinza)

---

## Issue 6: Validar reset de usos do Breath Weapon em descanso

**Tipo:** Bug potencial / validação  
**Prioridade:** Alta (afeta gameplay crítico)  
**Status:** Pendente

### Descrição do problema

Dragonborn Breath Weapon tem **1 uso por descanso** (curto ou longo).

**O que existe:**
- `classResources.dragonbornBreathWeapon.usesRemaining` → carregado e sincronizado
- `apply_dragonborn_breath_weapon_canonical_state` → garante `usesRemaining <= usesMax`
- Arma pode ser disparada (consome `usesRemaining`)

**O que não está confirmado:**
- **Reset em descanso curto** — `usesRemaining` volta a `usesMax = 1`?
- **Reset em descanso longo** — idem?

Sem reset, o jogador usa o sopro 1×, e fica indisponível para sempre — bug severo.

### Regra esperada

PHB 2014, Dragonborn — Breath Weapon:
> "Você pode usar sua ação para exalar destruição. [...] Quando você termina um descanso curto ou longo,
> você recupera o uso deste traço."

("Curto ou longo" = descanso **curto**, não apenas longo.)

### Arquivos envolvidos

**Fluxo de descanso:**
- [`apps/control-server/app/services/session_state_finalize.py:ensure_rest_state`](../apps/control-server/app/services/session_state_finalize.py)
  — procura por lógica de reset de recursos

- [`apps/control-server/app/services/class_progression.py`](../apps/control-server/app/services/class_progression.py)
  — pode ter função de "apply_rest" ou similar

- Procurar: onde `classResources` é resetada (spellSlots, hit dice, etc.)

**Ação de descanso:**
- Verificar se há endpoint `/api/rest` ou similar que marca `restType="short"|"long"`

**Testes existentes:**
- Procurar `test_*rest*.py` para entender o fluxo

### Risco estimado

**Baixo.** Se reset não existe, adicioná-lo é uma correção straightforward: zerar `usesRemaining` → `usesMax`
quando `restType` está no payload. Risco de regressão: garantir que **outros** recursos 
(spellSlots, hit dice) continuam resetando corretamente.

### Critérios de aceite

- [ ] Dragonborn usa Breath Weapon (1/1 → 0/1)
- [ ] Realiza descanso curto: `usesRemaining` volta a 1 ✅
- [ ] Usa novamente: funciona
- [ ] Sem descanso entre usos: falha (sem uso restante) ✅
- [ ] Descanso longo: reset continua funcionando (não quebra)

### Testes necessários

**Unitários:**
- [ ] `ensure_rest_state(data_with_dragonborn_exhausted, rest_type="short")` 
  → `usesRemaining = 1` (restaurado)
- [ ] `ensure_rest_state(data_with_dragonborn_exhausted, rest_type="long")`
  → `usesRemaining = 1`
- [ ] Sem `rest_type` no payload: `usesRemaining` não muda (não faz reset)

**Integração:**
- [ ] Combate: Dragonborn nível 5
  - Turno 1: usa Breath Weapon → `usesRemaining = 0/1`
  - Tenta usar novamente: falha (indisponível)
  - Fora de combate: realiza descanso curto
  - Volta ao combate: tenta usar → funciona (`usesRemaining = 0/1` novamente)

---

## Issue 7: Validar comportamento de Breath Weapon e Draconic traits durante Wild Shape

**Tipo:** Validação / bug potencial  
**Prioridade:** Média (caso de borda, afeta Druid/multiclasse)  
**Status:** Pendente

### Descrição do problema

Multiclasse ou híbrido: Dragonborn Druid, ou Sorcerer Draconic Druid.

Quando entra em Wild Shape (ação bônus, transforma em fera):
- HP da fera **substitui** o HP do personagem (não está adicionado)
- CA da fera **substitui** a CA do personagem (Draconic Resilience 13+Des é ignorada)
- Ao voltarvoltar da Wild Shape: HP e CA do personagem são restaurados

**Questões não confirmadas:**
1. **Resistência dracônica** persiste durante Wild Shape?
   - RAW: traços raciais (como resistências) **continuam durante Wild Shape**, mas traços de classe 
     que dependem do corpo humanóide (asas, foco de feitiço) não.
   - Esperado: resistência de Dragonborn sim; Elemental Affinity (classe) talvez não (debate).

2. **HP +1/nível de Sorcerer Draconic** continua? 
   - RAW: HP máximo é uma propriedade do personagem (não da forma). Ao retornar da Wild Shape, 
     HP máximo é restaurado com o bônus.
   - Esperado: sim, continua após retornar.

3. **Breath Weapon está disponível em Wild Shape?**
   - RAW: Dragonborn Breath Weapon é um traço racial → **não** funciona enquanto é uma fera (corpo diferente).
   - Esperado: não está disponível (precisa humanóide).

### Regra esperada

PHB 2014, Druid — Wild Shape:
> "Seus níveis de classe não mudam. Uma criatura é limitada a formas com nível de desafio (CD) 
> até 1/4 do seu nível. [...] **Seus atributos mudam para os da criatura, mas você retém seus valores 
> de inteligência, sabedoria e carisma.**"

E mais relevante:
> "Quando você retorna à sua forma verdadeira, você volta com seus pontos de vida anteriores."

Resistências raciais são traços que continuam (você é ainda um Dragonborn, anatomicamente diferente, 
mas resistências são intrínsecas).

### Arquivos envolvidos

**Transição Wild Shape (ativa):**
- [`apps/control-server/app/services/combat_service/actions/wild_shape.py`](../apps/control-server/app/services/combat_service/actions/wild_shape.py)
  — procura por lógica de aplicação de forma

**Finalize:**
- [`apps/control-server/app/services/session_state_finalize.py:337–366`](../apps/control-server/app/services/session_state_finalize.py#L337-L366)
  — trata Wild Shape ativo:
  ```python
  if wild_shape.get("active"):
      next_data["armorClass"] = form.armor_class  # ← CA substitui Draconic Resilience
      next_data.pop("armorClassFormulaCandidates", None)
  ```

**Resistências:**
- [`apps/control-server/app/services/combat_service/damage_core.py:49–53`](../apps/control-server/app/services/combat_service/damage_core.py#L49-L53)
  — `_apply_player_damage_resistances` chama `resolve_draconic_lineage_state(data)` e 
  `resolve_dragonborn_lineage_state(data)` — mantém resistências mesmo com Wild Shape ativo?

### Risco estimado

**Médio.** Requer testes de transição. Risco: se código assume que Wild Shape = "nada de traços raciais",
pode quebrar resistência indevidamente.

### Critérios de aceite

- [ ] **Resistência Dragonborn:** mantém durante Wild Shape (fogo ÷2, etc.) ✅
- [ ] **HP +1/nível Draconic Resilience:** restaurado corretamente ao sair de Wild Shape
  (ex.: saiu com 20 HP, forma tinha 15 HP, volta com 20 HP original preservado)
- [ ] **Breath Weapon:** não está disponível durante Wild Shape (ação desabilitada em UI)
- [ ] **CA Draconic Resilience 13+Des:** substituída por CA da fera durante Wild Shape, restaurada após
- [ ] **Elemental Affinity (resistência temporária):** persiste ou não? → definir se "resistência de classe"
  é cortada em Wild Shape (similar a foco de feitiço)
- [ ] **Capacidade de lançar feitiços:** não muda (pode lançar Sorcerer feitiços enquanto é fera?)
  — nota: isso depende da decisão de design, pode estar errado em qualquer código

### Testes necessários

**Unitários:**
- [ ] Dragonborn + Druid, em Wild Shape de lobo (forma lvl 1):
  - Resistência dracônica de fogo: `resolve_dragonborn_lineage_state(wild_shape_active)` 
    → deve retornar `resistances: ["fire"]` ✅
  - Breath Weapon: ação **desabilitada** (verificar condição)

**Integração:**
- [ ] Combate: Dragonborn Druid (vermelho), HP máximo 28 (20 base + 6 nível + 2 CON = 28)
  - Toma 10 dano: HP = 18
  - Usa Wild Shape (lobo, 20 HP):
    - Visualmente: HP = 20 (HP da forma)
    - AC = forma AC (ex.: 12)
    - Resistência a fogo: continua (toma fogo 10 → 5)
  - Sai de Wild Shape:
    - Volta com HP = 18 (o que tinha)
    - CA volta a Draconic Resilience 15 (13+2 Des)
    - Breath Weapon: ação reabilitada

- [ ] Sorcerer Draconic + Druid, mesmo teste mas com HP = Sorcerer base (20 + 6 + 2 = 28):
  - Verificar que recompute ao entrar/sair

---

## Resumo de prioridades

| Issue | Tipo | Prioridade | Esforço estimado | Bloqueador? |
|---|---|---|---|---|
| 1 — Escalonamento sopro 5→6 | Bug | 🔴 Alta | 1h (2 linhas) | Não |
| 2 — Elemental Affinity dano | Gap funcional | 🔴 Alta | 4h (pipeline) | Sim (gameplay) |
| 3 — Elemental Affinity resistência RAW | Divergência | 🔴 Alta | 6h (novo modelo) | Não (regra) |
| 4 — Dragon Wings (lvl 14) | Feature | 🟡 Média | 3h (ação + efeito) | Não |
| 5 — Draconic Presence (lvl 18) | Feature | 🟡 Média | 5h (área + concentração) | Não |
| 6 — Reset breath weapon em descanso | Validação | 🔴 Alta | 1h (verificar/corrigir) | Sim (crítico) |
| 7 — Wild Shape + traits dracônicos | Validação | 🟡 Média | 2h (testes) | Não |

---

## Próximos passos

1. **Triage:** revisar com product/design se há reordenação de prioridades
2. **Implementação:** começar pelas issues 🔴 (1, 2, 3, 6) em paralelo
3. **Features:** issues 4–5 podem vir depois (nível alto, menos urgência)
4. **Testes:** cada issue exige antes de merge
