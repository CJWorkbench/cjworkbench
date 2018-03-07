import React from 'react'

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
    return(
      <div className="embed-wrapper">
        <iframe src={"/api/wfmodules/" + this.props.wf_module.id + "/output"} />
        <div className="embed-info">
          <div className="embed-info-logo">
            <img src="/static/images/logo.png" width="21" />
          </div>
          <div className="embed-info-meta">
            <div className="t-d-gray mb-2 title-4">
              {this.props.workflow.name}
            </div>
            <div className="wf-meta--id">
              <ul className="WF-meta">
                <li className="WF-meta--item content-3 t-m-gray">
                  by {this.props.workflow.owner_name}
                </li>
                <li className="content-3 metadataSeparator t-m-gray">-</li>
                <li className="WF-meta--item content-3 t-m-gray">
                  Updated
                </li>
                <li className="WF-meta--item content-3 t-m-gray">
                </li>
              </ul>
            </div>
          </div>
          <div onClick={this.toggleOverlay} className="embed-info-button">
            <i className="icon icon-share"/>
          </div>
        </div>
        <div className={"embed-overlay" + (this.state.overlayOpen ? ' open' : '')} onClick={this.toggleOverlay}>
          <div className="embed-share-links">
            <h3>Share</h3>
            <ul className="embed-share-links--list">
              <li>Facebook</li>
              <li>Twitter</li>
              <li>Link</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }
}