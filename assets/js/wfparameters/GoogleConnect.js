import React from 'react';
import { store,  updateCurrentUserAction, reloadWorkflowAction, wfModuleStatusAction } from '../workflow-reducer';

export default class GoogleConnect extends React.Component {
  constructor(props) {
    super(props);
    this.oauthDialog = this.oauthDialog.bind(this);
    this.closeIt = this.closeIt.bind(this);
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

  closeIt() {
    this.state.popup.close()
  }

  render () {
    var renderOutput;
    if (this.props.userCreds.length === 0) {
      renderOutput = (<button onClick={this.oauthDialog}>Connect to Google</button>);
    } else {
      renderOutput = (<p>Connected to Google</p>)
    }
    return(
      <div className="parameter-margin">
        {renderOutput}
      </div>
    )
  }
}
