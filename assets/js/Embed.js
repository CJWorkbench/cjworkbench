import React from 'react'
import { escapeHtml, timeDifference } from './utils'
import { i18n } from '@lingui/core'
import { t, Trans } from '@lingui/macro'

export default class Embed extends React.Component {
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
          <h1><Trans id='js.Embed.workflowNotAvailable.title'>This workflow is not available</Trans></h1>
        </div>
        <div className='embed-footer'>
          <div className='embed-footer-logo'>
            <img src={`${window.STATIC_URL}images/logo.png`} width='21' />
          </div>
          <div className='embed-footer-meta'>
            <h1>
              <Trans id='js.Embed.workflowNotAvailable.footer.logo' comment='This should be all-caps for styling reasons'>
                    WORKBENCH
              </Trans>
            </h1>
          </div>
          <div className='embed-footer-button'>
            <i className='icon icon-share' />
          </div>
        </div>
      </div>
    )
  }

  render () {
    if (!this.props.workflow && !this.props.step) {
      return this.renderNotAvailable()
    }
    const iframeCode = escapeHtml('<iframe src="' + window.location.protocol + '//' + window.location.host + '/embed/' + this.props.step.id + '" width="560" height="315" frameborder="0"></iframe>')
    const timeAgo = timeDifference(this.props.workflow.last_update, new Date(), i18n)

    return (
      <div className='embed-wrapper'>
        <iframe src={'/api/wfmodules/' + this.props.step.id + '/output'} frameBorder={0} />
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
                      <Trans id='js.Embed.metadata.author'>by {this.props.workflow.owner_name}</Trans>
                    </a>
                  </li>
                  <li>
                    <a href={'/workflows/' + this.props.workflow.id} target='_blank' rel='noopener noreferrer'>
                      {t({
                        comment: "{timeAgo} will contain a time difference (i.e. something like '4h ago')",
                        id: 'js.Embed.metadata.updated',
                        message: 'Updated {timeAgo}',
                        values: { timeAgo }
                      })}
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
            <h1><Trans id='js.Embed.embedThisChart' comment='This should be all-caps for styling reasons'>EMBED THIS CHART</Trans></h1>
            <h2><Trans id='js.Embed.embedCode'>Paste this code into any webpage HTML</Trans></h2>
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
}
