import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default class RefineClustererProgress extends React.PureComponent {
  static propTypes = {
    progress: PropTypes.number.isRequired
  }

  render () {
    return (
      <div className='refine-clusterer-progress'>
        <progress value={this.props.progress} />
        <div className='message'><Trans id='js.params.Custom.RefineClustererProgress.findingClusters'>Finding clusters…</Trans></div>
      </div>
    )
  }
}
