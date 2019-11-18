import React from 'react'
import { escapeHtml, timeDifference } from './utils'
import { withI18n } from '@lingui/react'
import { t, Trans } from '@lingui/macro'
import PropTypes from 'prop-types'

export class Embed extends React.Component {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    })
  }

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
              <Trans id='js.Embed.workflowNotAvailable.footer.logo' description='This should be all-caps for styling reasons'>
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
    if (!this.props.workflow && !this.props.wf_module) {
      return this.renderNotAvailable()
    }
    const iframeCode = escapeHtml('<iframe src="' + window.location.protocol + '//' + window.location.host + '/embed/' + this.props.wf_module.id + '" width="560" height="315" frameborder="0" />')
    const timeAgo = timeDifference(this.props.workflow.last_update, new Date(), this.props.i18n)

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
                      {this.props.i18n._(
                        /* i18n: {timeAgo} will contain a time difference (i.e. something like '4h ago') */
                        t('js.Embed.metadata.updated')`Updated ${timeAgo}`
                      )}
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
            <h1><Trans id='js.Embed.embedThisChart' description='This should be all-caps for styling reasons'>EMBED THIS CHART</Trans></h1>
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
export default withI18n()(Embed)
