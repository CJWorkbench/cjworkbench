import { t } from '@lingui/macro'

const CategoryNames = {
  Combine: t('js.util.ModuleCategory.CategoryNames.Combine')`Combine`,
  Scrape: t('js.util.ModuleCategory.CategoryNames.Scrape')`Scrape`,
  Clean: t('js.util.ModuleCategory.CategoryNames.Clean')`Clean`,
  Analyze: t('js.util.ModuleCategory.CategoryNames.Analyze')`Analyze`,
  Visualize: t('js.util.ModuleCategory.CategoryNames.Visualize')`Visualize`,
  Code: t('js.util.ModuleCategory.CategoryNames.Code')`Code`,
  'Add data': t('js.util.ModuleCategory.CategoryNames.AddData')`Add data`
}

export function getCategoryName (i18n, category) {
  if (CategoryNames[category]) return i18n._(CategoryNames[category])
  else throw new Error('No such category: ' + category)
}
