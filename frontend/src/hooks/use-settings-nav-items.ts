import { useConfig } from "#/hooks/query/use-config";
import { SAAS_NAV_ITEMS, OSS_NAV_ITEMS } from "#/constants/settings-nav";

export function useSettingsNavItems() {
  const { data: config } = useConfig();

  const shouldHideLlmSettings = !!config?.feature_flags?.hide_llm_settings;
  const shouldHideUsersPage = !!config?.feature_flags?.hide_users_page;
  const shouldHideBillingPage = !!config?.feature_flags?.hide_billing_page;
  const shouldHideIntegrationsPage =
    !!config?.feature_flags?.hide_integrations_page;

  const isSaasMode = config?.app_mode === "saas";

  const items = isSaasMode ? SAAS_NAV_ITEMS : OSS_NAV_ITEMS;

  return items.filter((item) => {
    if (shouldHideLlmSettings && item.to === "/settings") return false;
    if (shouldHideUsersPage && item.to === "/settings/user") return false;
    if (shouldHideBillingPage && item.to === "/settings/billing") return false;
    if (shouldHideIntegrationsPage && item.to === "/settings/integrations")
      return false;
    return true;
  });
}
