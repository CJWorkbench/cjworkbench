import React from 'react'
import { Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import dateFormat from 'dateformat'
import * as Actions from '../workflow-reducer'
import PropTypes from 'prop-types'


export default class DataVersionSelect extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      modalOpen: false,
      dropdownOpen: false,
      versions: {versions: [], selected: ''},
      originalSelected: null
    };
    this.toggleModal = this.toggleModal.bind(this);
    this.toggleDropdown = this.toggleDropdown.bind(this);
    this.setSelected = this.setSelected.bind(this);
    this.changeVersions = this.changeVersions.bind(this);
  }

  // Takes a date string, interpreted as UTC, and produce a string for user display in user tz
  formatDate(datestr) {

    // dates already arrive in UTC
    var d = new Date(datestr);

    // check if we have a valid date
    if (isNaN(d.getTime())) return null;

    // return time as a user-readable string - "true" to convert to UTC for tests
    if (this.props.testing) {
      return dateFormat(d, "mmm d, yyyy - hh:MM TT", true)
    } else {
      return dateFormat(d, "mmm d, yyyy - hh:MM TT")
    }
  }

  toggleModal() {
    if (!this.props.isReadOnly) {
      // If we're closing the modal we need to set the current data version
      // to 'read'.
      var nextState = {
        modalOpen: !this.state.modalOpen
      }

      if (!this.state.modalOpen === false) {
        var idx = this.state.versions.versions.map((vers) => {
          return vers[0]
        }).indexOf(this.state.versions.selected);

        // If the selected version is false,
        if (!this.state.versions.versions[idx][1]) {
          // Copy the versions
          var nextVersions = JSON.parse(JSON.stringify(this.state.versions));
          // Set the read bit on the copy of the selected state to 'true'
          nextVersions.versions[idx][1] = true;

          // Add to the state we're changing
          nextState.versions = nextVersions;

          // Persist the change to the db
          Actions.store.dispatch(
            Actions.markDataVersionsReadAction(
              this.props.wfModuleId,
              nextVersions.versions[idx][0],
          ));
        };
      }
      this.setState(Object.assign({}, this.state, nextState));
    }
  }

  toggleDropdown() {
    if (this.props.isReadOnly) {
      this.setState(Object.assign({}, this.state, { dropdownOpen: !this.state.dropdownOpen }));
    }
  }

  toggleNotifications() {
    Actions.store.dispatch(
      Actions.updateWfModuleAction(
        this.props.wfModuleId,
        { notifications: !this.props.notifications }
    ));
  }

  loadVersions() {
    this.props.api.getWfModuleVersions(this.props.wfModuleId)
      .then(json => {
        this.setState(
          Object.assign({}, this.state, {versions: json, originalSelected: json.selected})
        );
      })
  }

  // Load version list / current version when first created
  componentDidMount() {
    this.loadVersions();
    this.props.setClickNotification(this.toggleModal);
  }

  // If the workflow revision changes, reload the versions in case they've changed too
  componentWillReceiveProps(nextProps) {
    if (this.props.revision != nextProps.revision) {
      this.loadVersions();
    }
  }

  setSelected(date) {
    if (!this.props.isReadOnly) {
      this.setState(
        Object.assign(
          {},
          this.state,
          {versions: {'versions': this.state.versions.versions, 'selected': date}}
        )
      );
    }
  }

  changeVersions() {
    if (this.state.versions.selected !== this.state.originalSelected) {
      this.props.api.setWfModuleVersion(this.props.wfModuleId, this.state.versions.selected)
      .then(() => {
        this.setState(
          Object.assign({}, this.state, {originalSelected: this.state.versions.selected})
        )
      })
    }

    this.toggleModal();
  }

  render() {
    var versionText;
    var modalLink;

    var totalVers = this.state.versions.versions.length;

    if (totalVers > 0) {
      var curVers = totalVers - this.state.versions.versions.map((version) => version[0]).indexOf(this.state.versions.selected);
      versionText = "Version " + curVers + " of " + totalVers;

      modalLink =
        <div>
          <div className='open-modal t-f-blue content-4 text-center' onClick={this.toggleModal}>
                {this.formatDate(this.state.originalSelected)}
          </div>
          <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className='modal-dialog'>
            <ModalHeader toggle={this.toggleModal} >
              <div className=''>Dataset Versions</div>
            </ModalHeader>
            <ModalBody className='list-body'>
              <div className=''>
                {this.state.versions.versions.map( version => {
                  return (
                    <div
                      key={version[0]}
                      className={
                        (version[0] == this.state.versions.selected)
                          ? 'line-item-data-selected list-test-class'
                          : 'line-item-data list-test-class'
                      }
                      onClick={() => this.setSelected(version[0])}
                    >
                      <span className='content-3'>{ this.formatDate(version[0]) }</span>
                      {!version[1] &&
                        <span className='icon icon-notification'></span>
                      }
                    </div>
                  );
                })}
              </div>
            </ModalBody>
            <ModalFooter className='dialog-footer'>
            {this.props.notifications ? (
              [<p key='1'>If a new version of the data is released at the source, a notification will be sent to your email address.</p>,
              <div key='2' className='button-gray mr-3 action-button test-cancel-button' onClick={() => {this.toggleNotifications(); this.toggleModal()}}>Cancel Alert</div>]
            ) : (
              [<p key='1'>If a new version of the data is released at the source, send a notification to your email address.</p>,
              <div key='2' className='button-gray mr-3 action-button test-cancel-button' onClick={() => {this.toggleNotifications(); this.toggleModal()}}>Set Alert</div>]
            )}
              <div className='button-blue action-button test-ok-button' onClick={this.changeVersions}>Apply</div>
            </ModalFooter>
          </Modal>
        </div>

    } else {
      versionText = "No data loaded";
      modalLink =
        <div className='open-modal t-f-blue content-4 text-center'>-</div>
    }

    return (
      <div className='version-item'>
        <div className='t-d-gray content-3 mb-2'>{versionText}</div>
        {modalLink}
      </div>
    );
  }
}

DataVersionSelect.propTypes = {
  wfModuleId:           PropTypes.number.isRequired,
  revision:             PropTypes.number.isRequired,
  api:                  PropTypes.object.isRequired,
  setClickNotification: PropTypes.func.isRequired,
  notifications:        PropTypes.bool,
  testing:              PropTypes.bool            // for testing only
};
