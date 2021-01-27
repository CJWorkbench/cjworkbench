import { t } from '@lingui/macro'

/**
 * List { path, title } pages.
 *
 * This is a function, not an export, because we run i18n on titles at call
 * time.
 */
export default function getSettingsPages () {
  return [
    {
      path: '/settings/billing',
      title: t({
        id: 'js.settings.settingsPages.billing.title',
        message: 'Billing'
      })
    },
    {
      path: '/settings/plan',
      title: t({
        id: 'js.settings.SettingsPages.plan.title',
        message: 'Plan'
      })
    }
  ]
}
