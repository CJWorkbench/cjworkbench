import React from 'react'
import PropTypes from 'prop-types'
import { plural, t } from '@lingui/macro'

export default function RefineStatus (props) {
  const { nBinsTotal } = props

  const statusText = (nBinsTotal === null)
    ? t({ id: 'js.params.Custom.RefineStatus.clustering', message: 'Clustering' })
    : t({
      id: 'js.params.Custom.RefineStatus.numberOfClustersFound',
      message: plural(nBinsTotal, {
        one: '# cluster found',
        other: '# clusters found'
      })
    })

  return (
    <div className='refine-status'>{statusText}</div>
  )
}
RefineStatus.propTypes = {
  nBinsTotal: PropTypes.number // or null when clustering
}
