import React from 'react'
import {escapeHtml, timeDifference} from './utils'

export default class Embed extends React.Component {
  constructor(props) {
    super(props);
    this.toggleOverlay = this.toggleOverlay.bind(this);
    this.renderNotAvailable = this.renderNotAvailable.bind(this);
    this.state = {
      overlayOpen: false
    }
  }

  toggleOverlay(e) {
    this.setState({
      overlayOpen: !this.state.overlayOpen
    })
  }

  renderNotAvailable() {
    return (
      <div className="embed-wrapper">
        <div className="embed-not-available">
          <h1>This workflow is not available</h1>
        </div>
        <div className="embed-info">
          <div className="embed-info-logo">
            <img src="/static/images/logo.png" width="21" />
          </div>
          <div className="embed-info-meta">
            <h1>WORKBENCH</h1>
          </div>
          <div className="embed-info-button">
            <i className="icon icon-share"/>
          </div>
        </div>
      </div>
    )
  }

  render() {
    if (!this.props.workflow && !this.props.wf_module) {
      return this.renderNotAvailable();
    }
    let iframeCode = escapeHtml('<iframe src="' + window.location.protocol + '//' + window.location.host + '/embed/' + this.props.wf_module.id + '" width="560" height="315" frameborder="0" />');

    return(
      <div className="embed-wrapper">
        <iframe src={"/api/wfmodules/" + this.props.wf_module.id + "/output"} frameborder="0"/>
        <div className="embed-info">
          <div className="d-flex align-items-center">
            <div className="embed-info-logo">
              <a href="/">
                <img src="/static/images/logo.png" width="35" />
              </a>
            </div>
            <div className="embed-info-meta">
              <div className="t-d-gray mb-1 title-4">
                <a href={"/workflows/" + this.props.workflow.id }>
                  {this.props.workflow.name}
                </a>
              </div>
              <div className="wf-meta--id">
                <ul className="WF-meta">
                  <div className="WF-meta--item content-3 t-m-gray">
                    <a href={"/workflows/" + this.props.workflow.id }>
                    by {this.props.workflow.owner_name}
                    </a>
                  </div>
                  <li className="content-3 metadataSeparator t-m-gray">-</li>
                  <li className="WF-meta--item content-3 t-m-gray">
                    <a href={"/workflows/" + this.props.workflow.id }>
                    Updated {timeDifference(this.props.workflow.last_update, new Date())}
                    </a>
                  </li>
                  <li className="WF-meta--item content-3 t-m-gray">
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div onClick={this.toggleOverlay} className="embed-info-button">
            <i className="icon icon-share"/>
          </div>
        </div>
        <div className={"embed-overlay" + (this.state.overlayOpen ? ' open' : '')} onClick={this.toggleOverlay}>
          <div className="embed-share-links" onClick={(e) => {e.stopPropagation()}}>
            <h1>Embed live chart using this code:</h1>
            <pre>
              <code className="embed--share-code">
                {iframeCode}
              </code>
            </pre>
          </div>
        </div>
      </div>
    );
  }
}
