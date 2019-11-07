import React from 'react'
import PropTypes from 'prop-types'
import { t, plural } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class RefineStatus extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    clustererProgress: PropTypes.number, // or null when clustered
    nBinsTotal: PropTypes.number // or null when clustering
  }

  render () {
    const { nBinsTotal, i18n } = this.props

    let statusText
    if (nBinsTotal === null) {
      statusText = i18n._(t('js.params.Custom.RefineStatus.clustering')`Clustering`)
    } else {
      statusText = i18n._(plural('js.params.Custom.RefineStatus.numberOfClustersFound', {
        value: nBinsTotal,
        one: '# cluster found',
        other: '# clusters found'
      }))
    }

    return (
      <div className='refine-status'>{statusText}</div>
    )
  }
}

export default withI18n()(RefineStatus)
