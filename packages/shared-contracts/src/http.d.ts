import { z } from "zod";
export declare const encounterSnapshotResponseSchema: z.ZodObject<{
    sessionId: z.ZodString;
    battleMap: z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        gridWidth: z.ZodNumber;
        gridHeight: z.ZodNumber;
        terrainVersion: z.ZodNumber;
        activeEncounterId: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        gridWidth: number;
        gridHeight: number;
        terrainVersion: number;
        activeEncounterId?: string | undefined;
    }, {
        id: string;
        name: string;
        gridWidth: number;
        gridHeight: number;
        terrainVersion: number;
        activeEncounterId?: string | undefined;
    }>;
    combatState: z.ZodObject<{
        id: z.ZodString;
        battleMapId: z.ZodString;
        status: z.ZodEnum<["inactive", "active", "completed"]>;
        roundNumber: z.ZodNumber;
        turnIndex: z.ZodNumber;
        activeCombatantId: z.ZodNullable<z.ZodString>;
        initiativeOrder: z.ZodArray<z.ZodString, "many">;
        advancedBy: z.ZodLiteral<"LimiarControl">;
        version: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        status: "inactive" | "active" | "completed";
        id: string;
        battleMapId: string;
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
        initiativeOrder: string[];
        advancedBy: "LimiarControl";
        version: number;
    }, {
        status: "inactive" | "active" | "completed";
        id: string;
        battleMapId: string;
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
        initiativeOrder: string[];
        advancedBy: "LimiarControl";
        version: number;
    }>;
    tokens: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        battleMapId: z.ZodString;
        label: z.ZodString;
        kind: z.ZodEnum<["playerCharacter", "ally", "enemy", "neutral"]>;
        controllerType: z.ZodEnum<["player", "gm", "limiarControl"]>;
        controllerId: z.ZodString;
        position: z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
        }, {
            x: number;
            y: number;
        }>;
        movementBudget: z.ZodNumber;
        combatantId: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        battleMapId: string;
        label: string;
        kind: "playerCharacter" | "ally" | "enemy" | "neutral";
        controllerType: "player" | "gm" | "limiarControl";
        controllerId: string;
        position: {
            x: number;
            y: number;
        };
        movementBudget: number;
        combatantId?: string | undefined;
    }, {
        id: string;
        battleMapId: string;
        label: string;
        kind: "playerCharacter" | "ally" | "enemy" | "neutral";
        controllerType: "player" | "gm" | "limiarControl";
        controllerId: string;
        position: {
            x: number;
            y: number;
        };
        movementBudget: number;
        combatantId?: string | undefined;
    }>, "many">;
    obstacles: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        battleMapId: z.ZodString;
        cells: z.ZodArray<z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
        }, {
            x: number;
            y: number;
        }>, "many">;
        blocksMovement: z.ZodBoolean;
        blocksTargeting: z.ZodBoolean;
    }, "strip", z.ZodTypeAny, {
        id: string;
        battleMapId: string;
        cells: {
            x: number;
            y: number;
        }[];
        blocksMovement: boolean;
        blocksTargeting: boolean;
    }, {
        id: string;
        battleMapId: string;
        cells: {
            x: number;
            y: number;
        }[];
        blocksMovement: boolean;
        blocksTargeting: boolean;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    sessionId: string;
    battleMap: {
        id: string;
        name: string;
        gridWidth: number;
        gridHeight: number;
        terrainVersion: number;
        activeEncounterId?: string | undefined;
    };
    combatState: {
        status: "inactive" | "active" | "completed";
        id: string;
        battleMapId: string;
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
        initiativeOrder: string[];
        advancedBy: "LimiarControl";
        version: number;
    };
    tokens: {
        id: string;
        battleMapId: string;
        label: string;
        kind: "playerCharacter" | "ally" | "enemy" | "neutral";
        controllerType: "player" | "gm" | "limiarControl";
        controllerId: string;
        position: {
            x: number;
            y: number;
        };
        movementBudget: number;
        combatantId?: string | undefined;
    }[];
    obstacles: {
        id: string;
        battleMapId: string;
        cells: {
            x: number;
            y: number;
        }[];
        blocksMovement: boolean;
        blocksTargeting: boolean;
    }[];
}, {
    sessionId: string;
    battleMap: {
        id: string;
        name: string;
        gridWidth: number;
        gridHeight: number;
        terrainVersion: number;
        activeEncounterId?: string | undefined;
    };
    combatState: {
        status: "inactive" | "active" | "completed";
        id: string;
        battleMapId: string;
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
        initiativeOrder: string[];
        advancedBy: "LimiarControl";
        version: number;
    };
    tokens: {
        id: string;
        battleMapId: string;
        label: string;
        kind: "playerCharacter" | "ally" | "enemy" | "neutral";
        controllerType: "player" | "gm" | "limiarControl";
        controllerId: string;
        position: {
            x: number;
            y: number;
        };
        movementBudget: number;
        combatantId?: string | undefined;
    }[];
    obstacles: {
        id: string;
        battleMapId: string;
        cells: {
            x: number;
            y: number;
        }[];
        blocksMovement: boolean;
        blocksTargeting: boolean;
    }[];
}>;
export declare const resyncRequestSchema: z.ZodObject<{
    lastKnownVersion: z.ZodNumber;
    clientInstanceId: z.ZodString;
}, "strip", z.ZodTypeAny, {
    lastKnownVersion: number;
    clientInstanceId: string;
}, {
    lastKnownVersion: number;
    clientInstanceId: string;
}>;
export declare const resyncResponseSchema: z.ZodObject<{
    resynced: z.ZodBoolean;
    snapshotVersion: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    resynced: boolean;
    snapshotVersion: number;
}, {
    resynced: boolean;
    snapshotVersion: number;
}>;
export type EncounterSnapshotResponse = z.infer<typeof encounterSnapshotResponseSchema>;
export type ResyncRequest = z.infer<typeof resyncRequestSchema>;
export type ResyncResponse = z.infer<typeof resyncResponseSchema>;
