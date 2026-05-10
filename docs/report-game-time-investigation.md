# Relatório Técnico: Estado Atual do Sistema de Tempo e Durações no LimiarControl

> Data: 2026-05-10  
> Escopo: Backend (`apps/control-server`), Frontend (`apps/control-web`), Tactical Engine (`packages/tactical-engine-py`)  
> Objetivo: Levantamento factual para viabilizar um futuro modelo de **tempo de jogo autoritativo**.

---

## 1. Resumo Executivo

O LimiarControl **não possui nenhum conceito de tempo de jogo (game_time)**. Todo tempo rastreado é wall clock (`datetime.now(timezone.utc)`). As durações de efeitos usam um sistema híbrido de tipos declarativos (rodadas, turnos) e tipos de lifecycle (até descanso, até remoção, manual), mas não há nenhuma unidade de tempo ficcional (horas, minutos, dias). Descansos são transações discretas de reset de recursos — não representam passagem de tempo. Iniciar/encerrar combate transfere efeitos entre dois stores distintos, mas sem nenhum relógio que conecte os dois domínios.

---

## 2. Arquitetura Atual Relevante

### 2.1 Tabelas principais

| Modelo | Tabela | Chave | Função |
|--------|--------|-------|--------|
| `Session` | `campaign_session` | `id` | Sessão de jogo (status, started_at, ended_at, duration_seconds) |
| `SessionState` | `session_state` | `(session_id, player_user_id)` | **Store canônico** do estado de cada jogador dentro de uma sessão |
| `SessionRuntime` | `session_runtime` | `session_id` (PK) | Estado operacional: lobby, shop_open, combat_active |
| `CombatState` | `combat_state` | `session_id` (unique) | Estado de combate: phase, round, participants, area_effects, anchors |
| `SessionCommandEvent` | `session_command_event` | `id` | Log de eventos da sessão (auditoria) |

### 2.2 Store canônico fora de combate

**`SessionState.state_json` (JSONB)** é o store canônico para dados de jogador fora de combate.

- **Modelo**: `app/models/session_state.py:10-22`
- **Campos**: `id`, `session_id`, `player_user_id`, `state_json`, `created_at`, `updated_at`
- `state_json` é um `dict` livre (sem schema Pydantic fixo no modelo) contendo tudo do personagem

### 2.3 Shape atual de `state_json` (inferido do código)

```jsonc
{
  // --- Atributos e recursos ---
  "abilities": { "strength": 10, "dexterity": 14, ... },
  "currentHP": 28,
  "maxHP": 30,
  "tempHP": 0,
  "level": 5,
  "class": "wizard",
  "deathSaves": { "successes": 0, "failures": 0 },

  // --- Equipamento ---
  "equippedArmor": { "armorType": "light", "baseAC": 12, ... },
  "equippedShield": { "bonus": 2 },
  "currentWeaponId": "uuid",
  "equippedArmorItemId": "uuid",

  // --- Magia ---
  "spellcasting": {
    "slots": { "1": { "max": 4, "used": 1 }, "2": { "max": 3, "used": 0 } },
    "spells": [ { "id": "...", "canonicalKey": "shield", "level": 1, "prepared": true } ]
  },

  // --- Estado de descanso ---
  "restState": "exploration",  // "exploration" | "short_rest" | "long_rest"
  "hitDiceType": "d6",
  "hitDiceTotal": 5,
  "hitDiceRemaining": 3,

  // --- Wild Shape ---
  "wildShape": { "active": false, "usesMax": 2, "usesRemaining": 2, ... },

  // --- Efeitos ativos persistidos (fora de combate) ---
  "active_spell_effects": [ ... ],  // Ver seção 3

  // --- Concentração ativa (derivada, não armazenada diretamente) ---
  // derive_active_concentration() lê de active_spell_effects

  // --- Preparação de magias pendente ---
  "pending_spell_preparation": { "source": "...", "preparedLimit": 6, ... },

  // --- Derivados (calculados por finalize_session_state_data) ---
  "armorClass": 15,
  "miscACBonus": 0,
  "fightingStyle": "defense"
}
```

### 2.4 Funções que criam/leem/finalizam `state_json`

| Função | Arquivo | Linha | Ação |
|--------|---------|-------|------|
| `finalize_session_state_data()` | `app/services/session_state_finalize.py` | 84 | Normaliza `restState`, recalcula `armorClass`, aplica breath weapon/wild shape |
| `merge_session_state_data()` | `app/services/session_state_merge.py` | 6 | Faz merge com base_sheet, preenchendo campos ausentes |
| `ensure_rest_state()` | `app/services/session_rest.py` | 30 | Garante que `restState` existe e é válido |
| `ensure_session_state()` | `app/api/routes/sessions/state_common.py` | — | Cria `SessionState` se não existe |

---

## 3. Fluxo Atual de Efeitos Persistidos Fora de Combate

### 3.1 Visão geral do ciclo de vida

```
  [Out-of-combat cast]          [Combat start]            [Combat end]
        │                            │                         │
  build_persisted_effects()    restore_persisted_effects()  persist_surviving_spell_effects()
        │                            │                         │
  state_json ──────────► participant.active_effects ──────► state_json
  (active_spell_effects)   (CombatState.participants)    (active_spell_effects)
```

### 3.2 Como um efeito declarativo fora de combate nasce

1. Jogador/GM chama `POST /sessions/{id}/state/me/spells/cast`
2. Rota: `app/api/routes/sessions/state.py:965`
3. Validação: `check_out_of_combat_cast_eligibility()` (`out_of_combat_cast.py:19`)
4. Criação: `build_persisted_effects()` (`out_of_combat_cast.py:68`)
5. Slot gasto: `consume_spell_slot()` (`out_of_combat_cast.py:193`)
6. Efeitos inseridos em `state_json["active_spell_effects"]`
7. Se alvo ≠ caster: marcador de concentração via `build_concentration_marker()` (`out_of_combat_cast.py:143`)
8. Estado salvo via `finalize_session_state_data()`

### 3.3 Shape de um efeito persistido (construído por `build_persisted_effects`)

```jsonc
{
  "id": "uuid",
  "source_participant_id": null,           // Sempre null fora de combate
  "kind": "spell_effect" | "temp_ac_bonus" | "<stat_name>",
  "condition_type": null,
  "numeric_value": null | 2,
  "duration_type": "until_long_rest",       // HARDCODED para fora de combate
  "remaining_rounds": null,
  "expires_on": null,
  "expires_at_participant_id": null,
  "created_at": "2026-05-10T12:00:00+00:00",  // datetime.now(timezone.utc).isoformat()
  "metadata": {
    "declarative_effect_group_id": "uuid",
    "declarative_effect": { "type": "...", "params": {...} },
    "declarative_on_end_effects": [],
    "source_spell_key": "barkskin",
    "source_spell_name": "Barkskin",
    "selected_variant_key": null,
    "selected_variant_label": null,
    "context_origin": "out_of_combat_cast",
    "concentration": false,
    "concentration_group": null,
    "caster_player_user_id": "user-uuid",
    "target_player_user_id": "user-uuid",
    // ...params mesclados para kind == "spell_effect"
  },
  "display_label": "Barkskin"
}
```

### 3.4 Restauração ao iniciar combate

- `restore_persisted_effects()` (`persistent_effects.py:72`)
- Chamado em `start_combat()` (`lifecycle_initiative.py:163`)
- Para cada jogador: lê `state_json["active_spell_effects"]`, filtra via `enforce_single_persisted_concentration_group()`, copia para `participant["active_effects"]`
- Não limpa `state_json` — efeitos ficam duplicados durante combate

### 3.5 Salvamento ao encerrar combate

- `persist_surviving_spell_effects()` (`persistent_effects.py:34`)
- Chamado em `end_combat()` (`lifecycle_turns.py:150`)
- Antes: concentração é limpa via `_clear_concentration_for_source()`
- Para cada jogador: filtra efeitos com `kind in {"spell_effect", "temp_ac_bonus"}` E `duration_type in {"manual", "until_long_rest", "until_short_rest", "until_removed"}`
- Sobrescreve `state_json["active_spell_effects"]` com os sobreviventes

### 3.6 Remoção manual

- `remove_persisted_effect()` (`persistent_effects.py:161`) — remove por ID, ou grupo inteiro se concentração
- `sync_effect_removal_to_state_json()` (`persistent_effects.py:122`) — sincroniza remoção do combate para state_json
- Endpoint: `DELETE /sessions/{id}/state/me/effects/{effect_id}`

### 3.7 Concentração persistida

- `derive_active_concentration()` (`persistent_effects.py:199`) — lê primeiro efeito com `metadata.concentration == true`
- `clear_persisted_concentration_effects()` (`persistent_effects.py:240`) — limpa por grupo ou todos
- `enforce_single_persisted_concentration_group()` (`persistent_effects.py:270`) — mantém apenas o grupo mais recente (por `created_at`)

### 3.8 Pruning/normalização

- Não existe pruning automático de efeitos por tempo. A única limpeza ocorre em descansos (via `_clear_rest_effects`) e na restauração ao iniciar combate (via `enforce_single_persisted_concentration_group`).

---

## 4. Modelo Atual de Duração

### 4.1 Durações declarativas (definição de magia)

Definido em `app/schemas/base_spell_effects.py:24-29`:

```python
SpellDeclarativeDurationType = Literal[
    "manual",
    "rounds",
    "until_turn_start",
    "until_turn_end",
]
```

E o schema `SpellDeclarativeDuration` (`base_spell_effects.py:63-80`):

```python
class SpellDeclarativeDuration(BaseModel):
    type: SpellDeclarativeDurationType
    rounds: int | None = Field(default=None, ge=1)
    anchor: Literal["target", "caster"] | None = None
```

**Fato**: Esses são **exclusivamente de combate**. Não existe no schema declarativo `until_long_rest`, `until_short_rest`, `until_removed`, horas, ou minutos.

### 4.2 Durações runtime (efeitos ativos)

Definido em `app/schemas/combat_actions.py:148-156`:

```python
ActiveEffectDurationType = Literal[
    "manual",
    "rounds",
    "until_turn_start",
    "until_turn_end",
    "until_long_rest",
    "until_short_rest",
    "until_removed",
]
```

Esse é o tipo que aparece em `ActiveEffect.duration_type` (`combat_actions.py:165`).

### 4.3 Classificação dos tipos

| Tipo | Domínio | Significado | Decrementado por |
|------|---------|-------------|-----------------|
| `manual` | Combat + OOC | GM/remove manualmente | Nada |
| `rounds` | Combat | N rodadas de combate | `_expire_effects_for_participant()` |
| `until_turn_start` | Combat | Até início do turno do participante | `_expire_effects_for_participant()` |
| `until_turn_end` | Combat | Até fim do turno do participante | `_expire_effects_for_participant()` |
| `until_long_rest` | OOC | Até descanso longo | `_clear_rest_effects()` |
| `until_short_rest` | OOC | Até descanso curto | `_clear_rest_effects()` |
| `until_removed` | OOC | Apenas remoção manual | Nada |

### 4.4 Efeitos OOC sempre recebem `until_long_rest`

Em `build_persisted_effects()` (`out_of_combat_cast.py:131`):

```python
"duration_type": "until_long_rest",
```

Isso é **hardcoded**. Independente da magia declarar `"manual"` ou qualquer outra duração, fora de combate tudo vira `until_long_rest`.

### 4.5 Persistência de efeitos por duration_type

Em `persistent_effects.py:26-31`:

```python
_PERSISTABLE_KINDS = {"spell_effect", "temp_ac_bonus"}
_PERSISTABLE_DURATION_TYPES = {
    "manual",
    "until_long_rest",
    "until_short_rest",
    "until_removed",
}
```

Efeitos com `duration_type in {"rounds", "until_turn_start", "until_turn_end"}` **não sobrevivem** ao fim do combate.

### 4.6 Campo `duration` em BaseSpell (texto editorial)

Em `app/models/base_spell.py:201` e `app/schemas/base_spell_read.py:52`:

```python
duration: Optional[str] = None  # editorial text, e.g. "Up to 1 hour", "Concentration, up to 10 minutes"
```

Este é texto livre para exibição no catálogo. **Não é parsed nem usado por lógica alguma**. As únicas aparições de "1 hour" no código estão em dados de teste:

- `tests/test_persistent_area_effects.py:80,273,370` — `"duration": "Up to 1 hour"` (texto editorial)

### 4.7 Campos de duração existentes no ActiveEffect

```python
# app/schemas/combat_actions.py:159-171
class ActiveEffect(BaseModel):
    duration_type: ActiveEffectDurationType = "manual"
    remaining_rounds: Optional[int] = None       # decrementado em combate
    expires_on: Optional[Literal["turn_start", "turn_end"]] = None
    expires_at_participant_id: Optional[str] = None
    created_at: str                               # wall clock ISO 8601
```

**Não existem**: `duration_rounds` (original), `expires_at` (timestamp), `duration_hours`, `duration_minutes`, ou qualquer campo de tempo ficcional.

---

## 5. Descansos Hoje

### 5.1 Endpoints

| Endpoint | Arquivo | Ação |
|----------|---------|------|
| (via commands) | `app/api/routes/sessions/commands_service.py` | Inicia/finaliza descanso via command |
| `POST /sessions/{id}/rest/use-hit-die` | `app/api/routes/sessions/rest.py:51` | Usa dado de vida durante short rest |

Descansos são controlados por commands do tipo `short_rest_start`, `short_rest_end`, `long_rest_start`, `long_rest_end` — processados em `commands_service.py`.

### 5.2 Estado

`state_json["restState"]` — um de `"exploration"`, `"short_rest"`, `"long_rest"`.

- Definido por `RestState = Literal["exploration", "short_rest", "long_rest"]` (`session_rest.py:14`)
- Normalizado por `normalize_rest_state()` e `ensure_rest_state()`

### 5.3 O que cada descanso faz

#### Short Rest (`session_rest.py:70-82`)

```python
# end_rest() → current_state == "short_rest"
next_data["restState"] = "exploration"
next_data = _recharge_wild_shape_inline(next_data)
next_data = _recharge_dragonborn_breath_weapon_inline(next_data)
next_data = _clear_rest_effects(next_data, "short_rest")
```

#### Long Rest (`session_rest.py:224-265`)

```python
# apply_long_rest()
next_data["currentHP"] = max_hp
next_data["deathSaves"] = {"successes": 0, "failures": 0}
next_data["tempHP"] = 0
next_data["hitDiceRemaining"] = min(hit_dice_total, hit_dice_remaining + recovered)
next_data["restState"] = "exploration"
# Recarrega spell slots (used = 0)
next_data = _force_revert_wild_shape_inline(next_data)
next_data = _recharge_wild_shape_inline(next_data)
next_data = _recharge_dragonborn_breath_weapon_inline(next_data)
next_data = _clear_rest_effects(next_data, "long_rest")
```

### 5.4 Limpeza de efeitos por descanso

`_clear_rest_effects()` (`session_rest.py:143-171`):

```python
if rest_type == "long_rest":
    cleared_types = {"manual", "until_long_rest", "until_short_rest"}
else:  # short_rest
    cleared_types = {"until_short_rest"}
```

- **Long rest** limpa: `manual`, `until_long_rest`, `until_short_rest`
- **Short rest** limpa: `until_short_rest`
- **Nunca limpa**: `until_removed`
- Efeitos legados sem `duration_type` são tratados como `manual` (limpos apenas em long rest)

### 5.5 Descanso como passagem de tempo?

**Não.** Descansos hoje são transações discretas de reset de recursos. Não existe nenhuma noção de "8 horas passaram" ou "1 hora passou". Não há clock, timer, ou acumulador associado.

---

## 6. Combate e Tempo Hoje

### 6.1 Representação de rounds e turns

Modelo `CombatState` (`app/models/combat.py:20-60`):

```python
class CombatState(SQLModel, table=True):
    phase: CombatPhase           # initiative | placement | active | ended
    round: int = Field(default=1)
    current_turn_index: int = Field(default=0)
    participants: list[dict]     # JSONB, cada um com active_effects
```

### 6.2 Avanço de turno

`next_turn()` (`lifecycle_turns.py:44-124`):

1. Valida ator ativo
2. **Expira efeitos** no outgoing participant: `_expire_effects_for_participant(..., "turn_end")`
3. `tick_spell_anchors_for_turn(..., trigger="turn_end")`
4. Incrementa `current_turn_index`; se >= `len(participants)`, reseta para 0 e `round += 1`
5. **Expira efeitos** no incoming participant: `_expire_effects_for_participant(..., "turn_start")`
6. `tick_spell_anchors_for_turn(..., trigger="turn_start")`
7. `_reset_turn_resources(incoming)` — reseta action/bonus_action/reaction

### 6.3 Decremento de durações em rodadas

`_expire_effects_for_participant()` (`effects_core.py:64-89`):

```python
if effect.get("duration_type") == "rounds":
    remaining = effect.get("remaining_rounds")
    if isinstance(remaining, int) and remaining > 1:
        effect["remaining_rounds"] = remaining - 1
        keep.append(effect)
        continue
    # else: expirou
```

O decremento é **por trigger de turno** (turn_start ou turn_end), não por rodada inteira. O efeito precisa estar associado ao participante cujo turno está sendo processado.

### 6.4 Iniciar combate

`start_combat()` (`lifecycle_initiative.py:146-184`):

1. Cria novo `CombatState` (deleta anterior se existir)
2. Para cada jogador: chama `restore_persisted_effects()` — copia `state_json["active_spell_effects"]` para `participant["active_effects"]`
3. `phase = initiative`, `round = 1`, `current_turn_index = 0`

### 6.5 Encerrar combate

`end_combat()` (`lifecycle_turns.py:127-176`):

1. Limpa **toda concentração** de todos participantes
2. `persist_surviving_spell_effects(db, state)` — salva efeitos sobreviventes em `state_json`
3. Limpa **todos** efeitos restantes dos participants
4. `phase = ended`, limpa `active_area_effects` e `spell_anchors`

### 6.6 Vínculo entre combate e fora de combate?

**Não existe.** A transferência é feita por cópia de dicts em dois momentos específicos (start/end combat). Não há referência cruzada, FK, ou sincronização contínua.

### 6.7 Um futuro game_time deve ser separado de round/turn?

**Fato**: Round e turn são abstrações de combate. O `round` em `CombatState` não representa tempo ficcional — representa a ordinalidade da rodada de combate. Efeitos com `duration_type: "rounds"` são desacoplados de qualquer tempo ficcional. **Um futuro game_time pode e deve ser completamente separado de round/turn.**

---

## 7. Timestamps Existentes e Risco de Confusão com Tempo de Jogo

### 7.1 Todos os usos de tempo

| Contexto | Campo/Ocorrência | Tipo | Natureza |
|----------|------------------|------|----------|
| `Session.started_at` | `models/session.py:31` | `datetime(tz)` | Wall clock — quando a sessão foi ativada |
| `Session.ended_at` | `models/session.py:34` | `datetime(tz)` | Wall clock — quando a sessão foi fechada |
| `Session.duration_seconds` | `models/session.py:37` | `int` | Wall clock — acumulado de `started_at` |
| `Session.created_at` | `models/session.py:40` | `datetime(tz)` | Infra — criação do registro |
| `Session.updated_at` | `models/session.py:43` | `datetime(tz)` | Infra — última atualização |
| `SessionState.created_at/updated_at` | `models/session_state.py:17-21` | `datetime(tz)` | Infra |
| `SessionRuntime.created_at/updated_at` | `models/session_runtime.py:30-34` | `datetime(tz)` | Infra |
| `CombatState.created_at/updated_at` | `models/combat.py:55-59` | `datetime(tz)` | Infra |
| `ActiveEffect.created_at` | `combat_actions.py:169` | `str` (ISO 8601) | **Wall clock** — quando o efeito foi criado |
| `SessionCommandEvent.created_at` | `models/session_command_event.py:20` | `datetime(tz)` | Infra/auditoria |
| `InventoryItem.expires_at` | `models/inventory.py:23` | `datetime(tz)` | **Wall clock** — expiração de item de inventário |
| `sessionOffsetSeconds` | `schemas/session.py:63+` | `int` | Wall clock — offset desde `started_at` |
| WebSocket `serverTime` | `ws_session.py:103`, `ws_campaign.py:80` | `str` | Wall clock — sincronização cliente |
| `ActiveEffect.created_at` (concentration selection) | `persistent_effects.py:314-333` | `str` | **Wall clock** — usado para selecionar grupo de concentração mais recente |

### 7.2 Risco de confusão

1. **`ActiveEffect.created_at`** (`concentration.py:72`, `out_of_combat_cast.py:91`): Usado para selecionar qual grupo de concentração manter. É wall clock. Se um futuro game_time for introduzido, este campo **não deve** mudar de significado — é infraestrutura para ordering.

2. **`InventoryItem.expires_at`** (`inventory.py:23`): Usado por Goodberry (24h wall clock) e consumíveis. É **wall clock real**, não tempo de jogo. Se um futuro game_time suportar "dura 24 horas de jogo", este campo precisará ser distinguido ou substituído.

3. **`sessionOffsetSeconds`** (`schemas/session.py`): Computado como `ts - started_at` em wall clock (`activity.py:60-64`). Usado apenas para exibição no feed de atividades. Não é tempo de jogo.

4. **`Session.duration_seconds`** (`models/session.py:37`): Acumulado de `started_at`. Wall clock puro.

### 7.3 Conclusão

**Não existe hoje nenhuma confusão entre tempo real e tempo de jogo, porque tempo de jogo simplesmente não existe.** A introdução de um game_time criará um novo conceito que precisará ser claramente separado de todos os timestamps acima.

---

## 8. Pontos Naturais de Extensão para um Futuro Relógio de Jogo

### 8.1 Onde guardar `game_time`

| Candidato | Vantagem | Desvantagem |
|-----------|----------|-------------|
| `SessionState.state_json` | Já é o store canônico por jogador | Game time é da sessão, não por jogador — criaria N cópias |
| `SessionRuntime` | Já guarda estado operacional por sessão (1:1 com session) | Precisa de migração/add column; semanticamente apropriado |
| Novo campo em `Session` | Simples, na tabela principal | `Session` é modelo "lento"; runtime é mais apropriado |
| Nova tabela `session_clock` | Totalmente separado | Overhead de mais uma tabela join |

**Recomendação preliminar (inferência)**: `SessionRuntime` parece o local mais natural — já é o singleton operacional da sessão.

### 8.2 Onde avançar o relógio

| Ponto | Arquivo | Função | Por quê |
|-------|---------|--------|---------|
| Descanso longo | `session_rest.py:224` | `apply_long_rest()` | Avançar N horas de jogo |
| Descanso curto | `session_rest.py:70` | `end_rest()` | Avançar 1 hora de jogo |
| Iniciar combate | `lifecycle_initiative.py:146` | `start_combat()` | Opcional: timestamp do início |
| Encerrar combate | `lifecycle_turns.py:127` | `end_combat()` | Opcional: timestamp do fim |
| Novo endpoint explícito | — | `advance_game_time()` | GM avança manualmente |

### 8.3 Onde consumir game_time para expiração de efeitos

| Ponto | Arquivo | Função | Ação futura |
|-------|---------|--------|-------------|
| `_clear_rest_effects` | `session_rest.py:143` | Limpeza de efeitos | Hoje usa `duration_type`; futuro pode comparar `effect.expires_at_game_time <= game_time` |
| `persist_surviving_spell_effects` | `persistent_effects.py:34` | Filtra sobreviventes | Futuro: filtrar efeitos expirados por game_time |
| `enforce_single_persisted_concentration_group` | `persistent_effects.py:270` | Seleciona concentração | Futuro: pode precisar considerar game_time, não apenas created_at |
| `build_persisted_effects` | `out_of_combat_cast.py:68` | Cria efeito OOC | Futuro: gravar `created_at_game_time` e calcular `expires_at_game_time` |

### 8.4 Onde a UI já seria candidata

| Componente | Arquivo | Hoje | Futuro |
|------------|---------|------|--------|
| `PlayerBoardStatusPanel` | `PlayerBoardStatusPanel.tsx` | Mostra efeitos com badge "Until long rest" | Adicionar badge "X hours remaining" |
| `getActiveEffectLifecycleBadges` | `activeEffectDisplay.ts:26` | Switch em `duration_type` | Novos cases para durações temporizadas |
| `SessionRuntimeRead` | `schemas/session.py:372` | `restState`, `combatActive` | Adicionar `gameTime` |
| Activity feed | `SessionActivityRowEvents*.tsx` | `sessionOffsetSeconds` | Adicionar game time offset |

---

## 9. Restrições Reais que um Desenho Futuro Precisa Respeitar

1. **`state_json` é schemaless** — qualquer novo campo (como `active_spell_effects[].expires_at_game_time`) será aceito sem migração, mas consumidores existentes precisam tolerá-lo.

2. **ActiveEffect é usado em dois domínios distintos** — dentro de `CombatState.participants[].active_effects` (combate) e `SessionState.state_json.active_spell_effects` (OOC). Qualquer campo novo precisa ser tolerado por ambos.

3. **`ActiveEffectDurationType` é um Literal** — adicionar novos valores (e.g., `"timed"`, `"game_hours"`) exigirá atualizar o schema em `combat_actions.py:148-156` e o tipo correspondente no frontend (`combatRepo.ts:40-47`).

4. **Efeitos OOC são hardcoded como `until_long_rest`** — `build_persisted_effects()` em `out_of_combat_cast.py:131` ignora a duração declarativa da magia. Um futuro sistema precisará resolver a duração declarativa para duração de jogo.

5. **`_PERSISTABLE_DURATION_TYPES`** em `persistent_effects.py:26-31` define quais efeitos sobrevivem ao fim do combate. Novos tipos de duração precisarão ser adicionados aqui.

6. **Concentração usa `created_at` (wall clock) para ordering** — `enforce_single_persisted_concentration_group()` em `persistent_effects.py:307-323` compara timestamps ISO string. Se game_time for introduzido, este ordering pode precisar mudar.

7. **`InventoryItem.expires_at` é wall clock** — Goodberry cria itens com `expires_at = now + 24h` real. Se a semântica mudar para "24h de jogo", este campo precisa ser repensado.

8. **A função `_clear_rest_effects`** é o único ponto onde efeitos são removidos por duração fora de combate. Qualquer expiração por game_time precisará ser chamada no mesmo ponto ou em novo ponto.

9. **Frontend espera `duration_type` como string literal** — `activeEffectDisplay.ts:40-84` faz switch exato nos valores atuais. Novos tipos precisam de novos cases.

10. **`sessionOffsetSeconds` é wall clock** — O feed de atividades usa offset real. Qualquer "game time offset" precisaria ser campo separado ou substituir o conceito.

11. **Não existe campo `duration` numérico nas magias** — `BaseSpell.duration` é texto editorial. Para suportar "8 horas" ou "24 horas" como duração de efeito, seria necessário parsear ou estender o schema declarativo.

---

## 10. Perguntas Ainda em Aberto / Incertezas

1. **Goodberry e itens temporários**: Hoje usam `InventoryItem.expires_at` com wall clock (24h reais). A semântica SRD é "24 horas". Um game_time deveria afetar isso?

2. **Efeitos de combate com duração declarativa "manual"**: Quando transferidos para OOC, viram `until_long_rest`. Isso está correto para magias como Bless que duram "Concentration, up to 1 minute"? Hoje Bless não sobrevive ao fim do combate (porque concentração é limpa primeiro), mas efeitos não-concentração com `duration_type: "manual"` viram `until_long_rest` automaticamente.

3. **Spell Anchors**: `spell_anchors` em `CombatState` usam `duration_type: "rounds"` exclusivamente. Não interagem com OOC. Mas seria útil saber se anchors deveriam ser afetados por game_time.

4. **Visibilidade do game_time**: O game_time seria visível apenas para GM, ou também para jogadores? A UI do player board teria um relógio?

5. **Sessões跨 (cross-session) persistence**: Efeitos persistidos em `state_json` sobrevivem ao fechamento da sessão? Se `game_time` for introduzido por sessão, como ficam efeitos que persistem entre sessões?

---

## O Que Eu Precisaria Decidir Antes de Desenhar o Relógio

1. **O game_time é por sessão ou por campanha?** Isto é, ao reabrir uma sessão (ou criar uma nova), o relógio continua de onde parou ou reseta?

2. **Qual é a granularidade mínima do game_time?** Minutos? Horas? Precisa suportar "1 rodada = 6 segundos" (SRD)?

3. **O game_time é apenas um contador avançado por ação (GM clica "avançar 8h"), ou também é avançado automaticamente por eventos (combate, viagem, descanso)?**

4. **Durações de magia SRD como "8 hours" ou "24 hours" devem ser interpretadas como tempo de jogo, ou continuam sendo representadas como `until_long_rest`?** Isto é: Armor of Agathys (1 hour) deve expirar após 1 hora de jogo, ou após descanso longo?

5. **Itens de inventário com `expires_at` (Goodberry, consumíveis) migram para game_time ou permanecem em wall clock?**

6. **A UI deve mostrar "X horas restantes" em efeitos com duração temporizada, ou mantém o modelo atual de badges semânticos ("Until long rest")?**

7. **Descansos avançam o relógio automaticamente?** Se sim, quanto? (SRD: short rest = 1+ hora, long rest = 8+ horas.)

8. **Efeitos existentes com `duration_type: "until_long_rest"` são migrados para o novo modelo, ou convivem?** Isto é: o novo sistema substitui o modelo de lifecycle ou o complementa?

9. **O GM pode retroceder o relógio?** Se sim, efeitos já expirados devem ser restaurados?

10. **Combate avança o game_time?** SRD diz que 1 rodada = 6 segundos, mas isso é raramente rastreado em VTTs.
