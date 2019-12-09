import React from 'react'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const CategoryNames = {
  Combine: t('js.util.ModuleCategoryName.CategoryNames.Combine')`Combine`,
  Scrape: t('js.util.ModuleCategoryName.CategoryNames.Scrape')`Scrape`,
  Clean: t('js.util.ModuleCategoryName.CategoryNames.Clean')`Clean`,
  Analyze: t('js.util.ModuleCategoryName.CategoryNames.Analyze')`Analyze`,
  Visualize: t('js.util.ModuleCategoryName.CategoryNames.Visualize')`Visualize`,
  Code: t('js.util.ModuleCategoryName.CategoryNames.Code')`Code`,
  'Add data': t('js.util.ModuleCategoryName.CategoryNames.AddData')`Add data`,
  Other: t('js.util.ModuleCategoryName.CategoryNames.Other')`Other`
}

export default withI18n()(({ category, i18n }) => {
  return <>{getCategoryName(category, i18n)}</>
})

/**
 * When you need the category name as a string, you may use this function
 */
export function getCategoryName (category, i18n) {
  if (CategoryNames[category]) return i18n._(CategoryNames[category])
  else throw new Error('No such category: ' + category)
}
