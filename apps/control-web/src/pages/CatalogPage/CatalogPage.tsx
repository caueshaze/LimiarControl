import { Navigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";

export const CatalogPage = () => <Navigate to={routes.catalogItems} replace />;
