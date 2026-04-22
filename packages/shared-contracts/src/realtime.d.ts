import { z } from "zod";
export declare const movementRequestSchema: z.ZodObject<{
    actionId: z.ZodString;
    sessionId: z.ZodString;
    tokenId: z.ZodString;
    path: z.ZodArray<z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>, "many">;
    knownVersion: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    path: {
        x: number;
        y: number;
    }[];
    actionId: string;
    tokenId: string;
    sessionId: string;
    knownVersion: number;
}, {
    path: {
        x: number;
        y: number;
    }[];
    actionId: string;
    tokenId: string;
    sessionId: string;
    knownVersion: number;
}>;
export declare const combatAdvanceRequestSchema: z.ZodObject<{
    actionId: z.ZodString;
    sessionId: z.ZodString;
    knownVersion: z.ZodNumber;
    requestedBy: z.ZodLiteral<"limiarControl">;
}, "strip", z.ZodTypeAny, {
    actionId: string;
    sessionId: string;
    knownVersion: number;
    requestedBy: "limiarControl";
}, {
    actionId: string;
    sessionId: string;
    knownVersion: number;
    requestedBy: "limiarControl";
}>;
export declare const targetingSubmitSchema: z.ZodObject<{
    actionId: z.ZodString;
    sessionId: z.ZodString;
    tokenId: z.ZodString;
    shape: z.ZodEnum<["line", "cone", "sphere", "cube", "cylinder"]>;
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
    knownVersion: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    actionId: string;
    tokenId: string;
    shape: "line" | "cone" | "sphere" | "cube" | "cylinder";
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
    sessionId: string;
    knownVersion: number;
}, {
    actionId: string;
    tokenId: string;
    shape: "line" | "cone" | "sphere" | "cube" | "cylinder";
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
    sessionId: string;
    knownVersion: number;
}>;
export declare const movementAppliedEventSchema: z.ZodObject<{
    eventId: z.ZodString;
    eventType: z.ZodString;
    encounterId: z.ZodString;
    version: z.ZodNumber;
    actionId: z.ZodOptional<z.ZodString>;
    replaySafe: z.ZodDefault<z.ZodBoolean>;
} & {
    payload: z.ZodObject<{
        tokenId: z.ZodString;
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
        pathCostUnits: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        position: {
            x: number;
            y: number;
        };
        tokenId: string;
        pathCostUnits: number;
    }, {
        position: {
            x: number;
            y: number;
        };
        tokenId: string;
        pathCostUnits: number;
    }>;
}, "strip", z.ZodTypeAny, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        position: {
            x: number;
            y: number;
        };
        tokenId: string;
        pathCostUnits: number;
    };
    replaySafe: boolean;
    actionId?: string | undefined;
}, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        position: {
            x: number;
            y: number;
        };
        tokenId: string;
        pathCostUnits: number;
    };
    actionId?: string | undefined;
    replaySafe?: boolean | undefined;
}>;
export declare const combatAdvancedEventSchema: z.ZodObject<{
    eventId: z.ZodString;
    eventType: z.ZodString;
    encounterId: z.ZodString;
    version: z.ZodNumber;
    actionId: z.ZodOptional<z.ZodString>;
    replaySafe: z.ZodDefault<z.ZodBoolean>;
} & {
    payload: z.ZodObject<Pick<{
        id: z.ZodString;
        battleMapId: z.ZodString;
        status: z.ZodEnum<["inactive", "active", "completed"]>;
        roundNumber: z.ZodNumber;
        turnIndex: z.ZodNumber;
        activeCombatantId: z.ZodNullable<z.ZodString>;
        initiativeOrder: z.ZodArray<z.ZodString, "many">;
        advancedBy: z.ZodLiteral<"LimiarControl">;
        version: z.ZodNumber;
    }, "roundNumber" | "turnIndex" | "activeCombatantId">, "strip", z.ZodTypeAny, {
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
    }, {
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
    }>;
}, "strip", z.ZodTypeAny, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
    };
    replaySafe: boolean;
    actionId?: string | undefined;
}, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        roundNumber: number;
        turnIndex: number;
        activeCombatantId: string | null;
    };
    actionId?: string | undefined;
    replaySafe?: boolean | undefined;
}>;
export declare const targetingResolvedEventSchema: z.ZodObject<{
    eventId: z.ZodString;
    eventType: z.ZodString;
    encounterId: z.ZodString;
    version: z.ZodNumber;
    actionId: z.ZodOptional<z.ZodString>;
    replaySafe: z.ZodDefault<z.ZodBoolean>;
} & {
    payload: z.ZodObject<{
        tokenId: z.ZodString;
        shape: z.ZodEnum<["line", "cone", "sphere", "cube", "cylinder"]>;
        affectedCells: z.ZodArray<z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
        }, {
            x: number;
            y: number;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        tokenId: string;
        shape: "line" | "cone" | "sphere" | "cube" | "cylinder";
        affectedCells: {
            x: number;
            y: number;
        }[];
    }, {
        tokenId: string;
        shape: "line" | "cone" | "sphere" | "cube" | "cylinder";
        affectedCells: {
            x: number;
            y: number;
        }[];
    }>;
}, "strip", z.ZodTypeAny, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        tokenId: string;
        shape: "line" | "cone" | "sphere" | "cube" | "cylinder";
        affectedCells: {
            x: number;
            y: number;
        }[];
    };
    replaySafe: boolean;
    actionId?: string | undefined;
}, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        tokenId: string;
        shape: "line" | "cone" | "sphere" | "cube" | "cylinder";
        affectedCells: {
            x: number;
            y: number;
        }[];
    };
    actionId?: string | undefined;
    replaySafe?: boolean | undefined;
}>;
export declare const actionRejectedEventSchema: z.ZodObject<{
    eventId: z.ZodString;
    eventType: z.ZodString;
    encounterId: z.ZodString;
    version: z.ZodNumber;
    actionId: z.ZodOptional<z.ZodString>;
    replaySafe: z.ZodDefault<z.ZodBoolean>;
} & {
    payload: z.ZodObject<{
        reason: z.ZodString;
        message: z.ZodString;
        details: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        reason: string;
        message: string;
        details?: string | undefined;
    }, {
        reason: string;
        message: string;
        details?: string | undefined;
    }>;
}, "strip", z.ZodTypeAny, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        reason: string;
        message: string;
        details?: string | undefined;
    };
    replaySafe: boolean;
    actionId?: string | undefined;
}, {
    version: number;
    eventId: string;
    eventType: string;
    encounterId: string;
    payload: {
        reason: string;
        message: string;
        details?: string | undefined;
    };
    actionId?: string | undefined;
    replaySafe?: boolean | undefined;
}>;
