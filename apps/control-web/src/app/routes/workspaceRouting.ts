import type { RoleMode } from "../../shared/types/role";
import { routes } from "./routes";

export type WorkspaceContext = {
  role: RoleMode;
  isSystemAdmin: boolean;
};

export const resolveHomePath = ({ role, isSystemAdmin }: WorkspaceContext) => {
  void isSystemAdmin;
  if (role === "GM") {
    return routes.gmHome;
  }
  return routes.home;
};

export const resolveWorkspaceMode = (role: RoleMode) =>
  role === "GM" ? "gm" : "player";
