import React from 'react'
import { escapeHtml, timeDifference } from './utils'
import { withI18n } from '@lingui/react'
import { Trans } from '@lingui/macro'

export default withI18n()(class Embed extends React.Component {
  state = {
    overlayOpen: false
  }

  handleToggleOverlay = (e) => {
    this.setState({
      overlayOpen: !this.state.overlayOpen
    })
  }

  renderNotAvailable () {
    return (
      <div className='embed-wrapper'>
        <div className='embed-not-available'>
          <h1><Trans id='workflow.notavailableworkflow'>This workflow is not available</Trans></h1>
        </div>
        <div className='embed-footer'>
          <div className='embed-footer-logo'>
            <img src={`${window.STATIC_URL}images/logo.png`} width='21' />
          </div>
          <div className='embed-footer-meta'>

            <h1><Trans id='workflow.workbenchheader'>WORKBENCH</Trans></h1>
          </div>
          <div className='embed-footer-button'>
            <i className='icon icon-share' />
          </div>
        </div>
      </div>
    )
  }

  render () {
    if (!this.props.workflow && !this.props.wf_module) {
      return this.renderNotAvailable()
    }
    const iframeCode = escapeHtml('<iframe src="' + window.location.protocol + '//' + window.location.host + '/embed/' + this.props.wf_module.id + '" width="560" height="315" frameborder="0" />')

    return (
      <div className='embed-wrapper'>
        <iframe src={'/api/wfmodules/' + this.props.wf_module.id + '/output'} frameBorder={0} />
        <div className='embed-footer'>
          <div className='metadata-stack'>
            <div className='embed-footer-logo'>
              <a href='http://workbenchdata.com' target='_blank' rel='noopener noreferrer'>
                <img src={`${window.STATIC_URL}images/logo.png`} width='35' />
              </a>
            </div>
            <div className='embed-footer-meta'>
              <div className='title'>
                <a href={'/workflows/' + this.props.workflow.id} target='_blank' rel='noopener noreferrer'>
                  {this.props.workflow.name}
                </a>
              </div>
              <div className='metadata'>
                <ul>
                  <li>
                    <a href={'/workflows/' + this.props.workflow.id} target='_blank' rel='noopener noreferrer'>
                    by {this.props.workflow.owner_name}
                    </a>
                  </li>
                  <li>
                    <a href={'/workflows/' + this.props.workflow.id} target='_blank' rel='noopener noreferrer'>
                   <Trans id='workflow.workbenchupdated'> Updated</Trans> {timeDifference(this.props.workflow.last_update, new Date(), this.props.i18n)}
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <button type='button' onClick={this.handleToggleOverlay} className='embed-footer-button'>
            <i className='icon icon-code' />
          </button>
        </div>
        <div className={'embed-overlay' + (this.state.overlayOpen ? ' open' : '')} onClick={this.handleToggleOverlay}>
          <div className='embed-share-links' onClick={(e) => { e.stopPropagation() }}>
            <h1><Trans id='workflow.workbenchembedheader'>EMBED THIS CHART</Trans></h1>
            <h2><Trans id='workflow.workbenchpastecodeheader'>Paste this code into any webpage HTML</Trans></h2>
            <div className='code-snippet'>
              <code className='embed--share-code'>
                {iframeCode}
              </code>
            </div>
          </div>
        </div>
      </div>
    )
  }
})
