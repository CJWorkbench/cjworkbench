import React from 'react'
import PropTypes from 'prop-types'
import { Trans,t } from '@lingui/macro'

export default class RefineClustererProgress extends React.PureComponent {
  static propTypes = {
    progress: PropTypes.number.isRequired
  }

  render () {
    return (
      <div className='refine-clusterer-progress'>
        <progress value={this.props.progress} />
        <div className='message'><Trans id="refineclustererprog.findingclusters">Finding clusters…</Trans></div>
      </div>
    )
  }
}
