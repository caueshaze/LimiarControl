export type CampaignEvent =
  | {
      type: "session_started";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        startedAt: string;
        title: string;
      };
      version?: number;
    }
  | { type: "session_closed"; payload: Record<string, unknown>; version?: number }
  | { type: "session_resumed"; payload: Record<string, unknown>; version?: number }
  | {
      type: "session_lobby";
      payload: {
        campaignId: string;
        partyId?: string | null;
        expectedPlayers: { userId: string; displayName: string }[];
        readyUserIds?: string[];
        readyCount?: number;
        totalCount?: number;
        sessionId: string;
        title: string;
      };
      version?: number;
    }
  | {
      type: "player_joined_lobby";
      payload: {
        displayName: string;
        partyId?: string | null;
        readyCount: number;
        readyUserIds?: string[];
        sessionId: string;
        totalCount: number;
        userId: string;
      };
      version?: number;
    }
  | {
      type: "shop_opened" | "shop_closed";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        issuedAt?: string;
        issuedBy?: string;
        shopOpen?: boolean;
      };
      version?: number;
    }
  | {
      type: "combat_started" | "combat_ended";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        issuedAt?: string;
        issuedBy?: string;
        combatActive?: boolean;
        note?: string;
      };
      version?: number;
    }
  | {
      type: "roll_requested";
      payload: {
        campaignId: string;
        expression: string;
        issuedAt?: string;
        issuedBy?: string;
        mode?: "advantage" | "disadvantage" | null;
        partyId?: string | null;
        reason?: string;
        rollType?: string | null;
        ability?: string | null;
        skill?: string | null;
        dc?: number | null;
        sessionId: string;
        targetUserId?: string | null;
      };
      version?: number;
    }
  | {
      type: "dice_rolled";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        userId?: string | null;
      };
      version?: number;
    }
  | {
      type: "shop_purchase_created";
      payload: {
        campaignId: string;
        itemId: string;
        itemName: string;
        partyId?: string | null;
        quantity: number;
        sessionId: string;
        userId?: string | null;
      };
      version?: number;
    }
  | {
      type: "shop_sale_created";
      payload: {
        campaignId: string;
        itemId: string;
        itemName: string;
        partyId?: string | null;
        quantity: number;
        refundLabel?: string;
        sessionId: string;
        userId?: string | null;
      };
      version?: number;
    }
  | {
      type: "party_member_updated";
      payload: {
        campaignId: string;
        partyId: string;
        role: "GM" | "PLAYER";
        status: string;
        userId: string;
      };
      version?: number;
    }
  | {
      type: "character_sheet_updated";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        characterSheetId: string;
        sourceDraftId?: string | null;
        deliveredAt?: string | null;
        acceptedAt?: string | null;
        updateKind: "created" | "updated" | "delivered" | "accepted";
      };
      version?: number;
    }
  | {
      type: "session_state_updated";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        sessionId: string;
        state?: unknown;
      };
      version?: number;
    }
  | {
      type: "gm_granted_currency";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        sessionId: string;
        currentCurrency?: {
          copperValue?: number;
        };
        grantedCurrency?: {
          copperValue?: number;
        };
      };
      version?: number;
    }
  | {
      type: "gm_granted_item";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        sessionId: string;
        itemId: string;
        itemName: string;
        quantity: number;
        inventoryItemId?: string | null;
      };
      version?: number;
    }
  | {
      type: "gm_granted_xp";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        sessionId: string;
        grantedAmount: number;
        currentXp: number;
        currentLevel: number;
        nextLevelThreshold: number | null;
      };
      version?: number;
    }
  | {
      type: "rest_started";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        issuedAt?: string;
        issuedBy?: string;
        restType: "short_rest" | "long_rest";
      };
      version?: number;
    }
  | {
      type: "rest_ended";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        issuedAt?: string;
        issuedBy?: string;
        restType: "short_rest" | "long_rest";
      };
      version?: number;
    }
  | {
      type: "hit_dice_used";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        playerUserId: string;
        roll: number;
        healingApplied: number;
        healingRolled: number;
        constitutionModifier: number;
        currentHp: number;
        maxHp: number;
        hitDiceRemaining: number;
        hitDiceTotal: number;
        hitDieType: string;
      };
      version?: number;
    }
  | {
      type: "consumable_used";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        actorUserId?: string | null;
        actorDisplayName?: string | null;
        inventoryItemId?: string | null;
        itemId?: string | null;
        itemName: string;
        consumedQuantity: number;
        remainingQuantity: number;
        targetKind: "player" | "session_entity";
        targetRefId: string;
        targetUserId?: string | null;
        targetDisplayName?: string | null;
        healingApplied: number;
        newHp: number;
        previousHp?: number | null;
        maxHp?: number | null;
        effectDice?: string | null;
        effectBonus?: number | null;
        effectRolls?: number[];
        effectRollSource?: "system" | "manual" | null;
        issuedAt?: string;
      };
      version?: number;
    }
  | {
      type: "level_up_requested" | "level_up_approved" | "level_up_denied";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        level: number;
        experiencePoints: number;
        pendingLevelUp: boolean;
      };
      version?: number;
    }
  | {
      type: "entity_revealed" | "entity_hidden";
      payload: {
        sessionId: string;
        campaignId: string;
        partyId?: string | null;
        sessionEntityId: string;
        campaignEntityId: string;
        visibleToPlayers: boolean;
        label?: string | null;
        currentHp?: number | null;
        entityName?: string | null;
        entityCategory?: string | null;
        maxHp?: number | null;
      };
      version?: number;
    }
  | {
      type: "entity_hp_updated";
      payload: {
        sessionId: string;
        campaignId: string;
        partyId?: string | null;
        sessionEntityId: string;
        campaignEntityId: string;
        visibleToPlayers: boolean;
        label?: string | null;
        currentHp?: number | null;
        entityName?: string | null;
        entityCategory?: string | null;
        maxHp?: number | null;
        previousHp?: number | null;
        hpDelta?: number | null;
      };
      version?: number;
    }
  | {
      type: "session_entity_added" | "session_entity_removed";
      payload: {
        sessionId: string;
        campaignId: string;
        partyId?: string | null;
        sessionEntityId: string;
        campaignEntityId: string;
        visibleToPlayers?: boolean;
        label?: string | null;
        currentHp?: number | null;
        entityName?: string | null;
        entityCategory?: string | null;
        maxHp?: number | null;
      };
      version?: number;
    }
  | {
      type: "roll_resolved";
      payload: {
        event_id: string;
        roll_type: string;
        actor_kind: string;
        actor_ref_id: string;
        actor_display_name: string;
        rolls: number[];
        selected_roll: number;
        advantage_mode: string;
        modifier_used: number;
        override_used: boolean;
        formula: string;
        total: number;
        ability?: string | null;
        skill?: string | null;
        dc?: number | null;
        target_ac?: number | null;
        success?: boolean | null;
        is_gm_roll: boolean;
        roll_source: string;
        sessionId: string;
        campaignId: string;
        partyId?: string | null;
      };
      version?: number;
    };
