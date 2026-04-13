import { z } from "zod";
export declare const coordinateSchema: z.ZodObject<{
    x: z.ZodNumber;
    y: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    x: number;
    y: number;
}, {
    x: number;
    y: number;
}>;
export declare const controllerTypeSchema: z.ZodEnum<["player", "gm", "limiarControl"]>;
export declare const actionResultSchema: z.ZodEnum<["pending", "accepted", "rejected"]>;
export declare const combatStatusSchema: z.ZodEnum<["inactive", "active", "completed"]>;
export declare const targetingShapeSchema: z.ZodEnum<["line", "cone", "sphere", "cube"]>;
export declare const battleMapSchema: z.ZodObject<{
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
export declare const obstacleSchema: z.ZodObject<{
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
}>;
export declare const tokenSchema: z.ZodObject<{
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
}>;
export declare const combatStateSchema: z.ZodObject<{
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
export declare const movementActionSchema: z.ZodObject<{
    actionId: z.ZodString;
    tokenId: z.ZodString;
    requestedPath: z.ZodArray<z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>, "many">;
    submittedBy: z.ZodString;
    submittedAtVersion: z.ZodNumber;
    result: z.ZodDefault<z.ZodEnum<["pending", "accepted", "rejected"]>>;
    rejectionReason: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    actionId: string;
    tokenId: string;
    requestedPath: {
        x: number;
        y: number;
    }[];
    submittedBy: string;
    submittedAtVersion: number;
    result: "pending" | "accepted" | "rejected";
    rejectionReason?: string | undefined;
}, {
    actionId: string;
    tokenId: string;
    requestedPath: {
        x: number;
        y: number;
    }[];
    submittedBy: string;
    submittedAtVersion: number;
    result?: "pending" | "accepted" | "rejected" | undefined;
    rejectionReason?: string | undefined;
}>;
export declare const targetingTemplateSchema: z.ZodObject<{
    actionId: z.ZodString;
    tokenId: z.ZodString;
    shape: z.ZodEnum<["line", "cone", "sphere", "cube"]>;
    originCell: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
    anchorCell: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
    range: z.ZodNumber;
    size: z.ZodNumber;
    affectedCells: z.ZodDefault<z.ZodArray<z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>, "many">>;
    result: z.ZodDefault<z.ZodEnum<["pending", "accepted", "rejected"]>>;
    rejectionReason: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    actionId: string;
    tokenId: string;
    result: "pending" | "accepted" | "rejected";
    shape: "line" | "cone" | "sphere" | "cube";
    originCell: {
        x: number;
        y: number;
    };
    anchorCell: {
        x: number;
        y: number;
    };
    range: number;
    size: number;
    affectedCells: {
        x: number;
        y: number;
    }[];
    rejectionReason?: string | undefined;
}, {
    actionId: string;
    tokenId: string;
    shape: "line" | "cone" | "sphere" | "cube";
    originCell: {
        x: number;
        y: number;
    };
    anchorCell: {
        x: number;
        y: number;
    };
    range: number;
    size: number;
    result?: "pending" | "accepted" | "rejected" | undefined;
    rejectionReason?: string | undefined;
    affectedCells?: {
        x: number;
        y: number;
    }[] | undefined;
}>;
export declare const realtimeActionEventSchema: z.ZodObject<{
    eventId: z.ZodString;
    eventType: z.ZodString;
    encounterId: z.ZodString;
    version: z.ZodNumber;
    actionId: z.ZodOptional<z.ZodString>;
    payload: z.ZodRecord<z.ZodString, z.ZodUnknown>;
    replaySafe: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: Record<string, unknown>;
    replaySafe: boolean;
    actionId?: string | undefined;
}, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: Record<string, unknown>;
    actionId?: string | undefined;
    replaySafe?: boolean | undefined;
}>;
export type Coordinate = z.infer<typeof coordinateSchema>;
export type ControllerType = z.infer<typeof controllerTypeSchema>;
export type BattleMap = z.infer<typeof battleMapSchema>;
export type Obstacle = z.infer<typeof obstacleSchema>;
export type Token = z.infer<typeof tokenSchema>;
export type CombatState = z.infer<typeof combatStateSchema>;
export type MovementAction = z.infer<typeof movementActionSchema>;
export type TargetingTemplate = z.infer<typeof targetingTemplateSchema>;
export type RealtimeActionEvent = z.infer<typeof realtimeActionEventSchema>;
