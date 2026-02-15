import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "../../features/auth";
import { CampaignProvider } from "../../features/campaign-select";
import { SessionProvider } from "../../features/sessions";
import { LocaleProvider } from "./LocaleProvider";

type AppProvidersProps = {
  children: ReactNode;
};

export const AppProviders = ({ children }: AppProvidersProps) => (
  <LocaleProvider>
    <AuthProvider>
      <CampaignProvider>
        <SessionProvider>
          <BrowserRouter>{children}</BrowserRouter>
        </SessionProvider>
      </CampaignProvider>
    </AuthProvider>
  </LocaleProvider>
);
