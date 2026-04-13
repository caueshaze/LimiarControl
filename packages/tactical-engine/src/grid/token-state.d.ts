import type { ControllerType, Coordinate, Token } from "@limiarmap/shared-contracts";
export interface TokenState extends Token {
    controllerType: ControllerType;
    position: Coordinate;
}
