import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default function ModuleCategoryName (props) {
  const { category } = props
  switch (category) {
    case 'Combine':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.Combine'>
          Combine
        </Trans>
      )
    case 'Scrape':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.Scrape'>
          Scrape
        </Trans>
      )
    case 'Clean':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.Clean'>Clean</Trans>
      )
    case 'Analyze':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.Analyze'>
          Analyze
        </Trans>
      )
    case 'Visualize':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.Visualize'>
          Visualize
        </Trans>
      )
    case 'Code':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.Code'>Code</Trans>
      )
    case 'Add data':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.AddData'>
          Add data
        </Trans>
      )
    case 'Other':
      return (
        <Trans id='js.util.ModuleCategoryName.CategoryNames.Other'>Other</Trans>
      )
  }
}
ModuleCategoryName.propTypes = {
  category: PropTypes.oneOf([
    'Combine',
    'Scrape',
    'Clean',
    'Analyze',
    'Visualize',
    'Code',
    'Add data',
    'Other'
  ]).isRequired
}
