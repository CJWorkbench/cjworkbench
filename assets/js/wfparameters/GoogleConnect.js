import React from 'react';
import { store,  updateCurrentUserAction, disconnectCurrentUserAction } from '../workflow-reducer';

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
        if (that.state.popup.location.pathname === '/oauth/') {
          that.state.popup.close();
          store.dispatch(updateCurrentUserAction());
          clearInterval(interval);
        }
      } catch(e) {
        //do nothing, we can't access the URL because of cross-origin policy
      }
    }, 500);
  }

  disconnect() {
    store.dispatch(disconnectCurrentUserAction(this.props.userCreds[0]))
  }

  closeIt() {
    this.state.popup.close()
  }

  render () {
    var renderOutput;
    if (this.props.userCreds.length === 0) {
      renderOutput = (
        <div>
          <div className="title-3 t-d-gray centered mb-1">Connect with Google</div>
          <div className="info-1 t-m-gray centered mb-3">Google spreadsheet, CSV supported</div>
          <button className='action-button button-orange centered' onClick={this.oauthDialog}>Connect</button>
        </div>
      );
    } else {
      renderOutput = (<p><span className="t-f-blue" onClick={this.disconnect}>Disconnect</span> account</p>)
    }
    return(
      <div className="parameter-margin connected-account">
        {renderOutput}
      </div>
    )
  }
}
