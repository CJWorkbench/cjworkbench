import React from 'react';
import { store,  getCurrentUserAction, disconnectCurrentUserAction } from '../workflow-reducer';

export default class GoogleConnect extends React.Component {
  constructor(props) {
    super(props);
    this.oauthDialog = this.oauthDialog.bind(this);
    this.closeIt = this.closeIt.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this.state = {
      popup: null
    }
  }

  oauthDialog() {
    var interval;
    var that = this;
    this.state.popup = window.open(
      '/authorize',
      '_blank',
      'height=500,width=400'
    )
    interval = window.setInterval(function () {
      try {
        if (/^\/oauth\/?/.test(that.state.popup.location.pathname)) {
          that.state.popup.close();
          store.dispatch(getCurrentUserAction());
          clearInterval(interval);
        }
      } catch(e) {
        //do nothing, we can't access the URL because of cross-origin policy
      }
    }, 500);
  }

  disconnect() {
    store.dispatch(disconnectCurrentUserAction(this.props.userCreds))
  }

  closeIt() {
    this.state.popup.close()
  }

  render () {
    var renderOutput;
    const { userCreds } = this.props

    if (!userCreds) {
      renderOutput = (
        <div className="gdrive-connectAccount">
          <button className='action-button button-orange' onClick={this.oauthDialog}>Connect account</button>
        </div>
      );
    } else {
      renderOutput = (<p><span className="t-f-blue" onClick={this.disconnect}>Disconnect</span> account</p>)
    }
    return(
      <div className="connected-account">
        {renderOutput}
      </div>
    )
  }
}
