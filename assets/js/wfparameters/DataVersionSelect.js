import React from 'react'
import { Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import dateFormat from 'dateformat'
import * as Actions from '../workflow-reducer'
import PropTypes from 'prop-types'
import {connect} from 'react-redux';


class DataVersionSelect extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      modalOpen: false,
      dropdownOpen: false,
      dialogSelected: null
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
      return dateFormat(d, "mmm d yyyy - hh:MMTT", true)
    } else {
      return dateFormat(d, "mmm d yyyy - hh:MMTT")
    }
  }

  toggleModal() {
    if (!this.props.isReadOnly) {
      if (!this.state.modalOpen === false) {
        // TODO: this.props.versions.selected should be a tuple of (<Date>, <Boolean>)
        // TODO: Don't do Array.find, it's slow
        let idx;
        for (let i = 0; i < this.props.versions.versions.length; i++) {
          idx = i;
          if (this.props.versions.selected === this.props.versions.versions[i][0]) {
            break;
          }
        }
        // If the selected version is false,
        if (!this.props.versions.versions[idx][1]) {
          // Persist the change to the db
          this.props.markDataVersionsReadAction(
            this.props.wfModuleId,
            this.props.versions.versions[idx][0],
          );
        }
      }

      this.setState({
        modalOpen: !this.state.modalOpen,
        dialogSelected: this.props.versions.selected
      });
    }
  }

  toggleDropdown() {
    if (this.props.isReadOnly) {
      this.setState(Object.assign({}, this.state, { dropdownOpen: !this.state.dropdownOpen }));
    }
  }

  toggleNotifications() {
    this.props.updateWfModuleAction(
      this.props.wfModuleId,
      { notifications: !this.props.notifications }
    );
  }

  // Set action to take when a user clicks on the notification icon
  componentDidMount() {
    this.props.setClickNotification(this.toggleModal);
  }

  // If the workflow revision changes, reload the versions in case they've changed too
  // TODO: Is this still necessary?
  componentWillReceiveProps(nextProps) {
    if (this.state.dialogSelected === null && nextProps.versions.selected) {
      this.setState({
        dialogSelected: nextProps.versions.selected
      });
    }
  }

  setSelected(date) {
    if (!this.props.isReadOnly) {
      this.setState(
        Object.assign(
          {},
          this.state,
          {dialogSelected: date}
        )
      );
    }
  }

  changeVersions() {
    if (this.props.versions.selected !== this.state.dialogSelected) {
      this.props.setDataVersionAction(this.props.wfModuleId, this.state.dialogSelected);
    }
    this.toggleModal();
  }

  render() {
    // This is here to fix a subtle bug that has to do with nested connected components that use the wrapped component's
    // own props to derive state, as this one does. (https://github.com/reactjs/react-redux/pull/99)
    // If mapStateToProps returns undefined, we don't want to try to render, because it means the module has already
    // been removed from state, but moduleStack hasn't re-rendered yet. This is the simple solution, but we may be able
    // to come up with a better, more general one.

    if (typeof this.props.versions === 'undefined') {
      return null;
    }

    var versionText;
    var modalLink;

    var totalVers = this.props.versions.versions ? this.props.versions.versions.length : 0;

    if (totalVers > 0) {
      var curVers = totalVers - this.props.versions.versions.map((version) => version[0]).indexOf(this.props.versions.selected);
      versionText = curVers + " of " + totalVers;

      modalLink =
        <div>
          <div className='open-modal t-f-blue content-3 ml-2' onClick={this.toggleModal}>
            {versionText}
          </div>
          <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className='modal-dialog'>
            <ModalHeader toggle={this.toggleModal} className='dialog-header'>
              <div className='title-4 t-d-gray'>DATA VERSIONS</div>
            </ModalHeader>
            <ModalBody className='list-body'>
              <div className=''>
                {this.props.versions.versions.map( version => {
                  return (
                    <div
                      key={version[0]}
                      className={
                        (version[0] == this.state.dialogSelected)
                          ? 'line-item--data-version--selected d-flex justify-content-between list-test-class'
                          : 'line-item--data-version d-flex justify-content-between list-test-class'
                      }
                      onClick={() => this.setSelected(version[0])}
                    >
                      <div className='content-3'>{ this.formatDate(version[0]) }</div>
                        {!version[1] &&
                          <div className='icon icon-notification mr-5'></div>
                        }
                      </div>
                  );
                })}
              </div>
            </ModalBody>
            <ModalFooter className='dialog-footer d-flex justify-content-between'>
            <div className='alert-setting-modal'>
              {this.props.notifications ? (
                [<div className='alert-setting' key='1'>
                  <div className='d-flex align-items-center mb-2'>
                    <div className='icon-notification t-orange module-icon mr-3'></div>
                    <div className='info-1 t-orange'>Alerts are ON</div>
                  </div>
                  <div> If new data is released, you will be notified via email.</div>
                </div>,
                <div key='2' className='button-gray action-button test-cancel-button' onClick={() => {this.toggleNotifications(); this.toggleModal()}}>Turn off</div>]
              ) : (
                [<div className='alert-setting' key='1'>
                  <div className='d-flex align-items-center mb-2'>
                    <div className='icon-notification module-icon mr-3'></div>
                    <div className='info-1'>Alerts are OFF</div>
                  </div>
                  <div>Turn alerts ON to be notified via email if new data is released.</div>
                </div>,
                <div key='2' className='button-gray action-button test-cancel-button' onClick={() => {this.toggleNotifications(); this.toggleModal()}}>Turn on</div>]
              )}
            </div>
              <div className='button-blue action-button test-ok-button' onClick={this.changeVersions}>Load</div>
            </ModalFooter>
          </Modal>
        </div>

    } else {
      versionText = "No data loaded";
      modalLink =
        <div className='open-modal t-f-blue content-3 ml-2'>-</div>
    }

    return (
      <div className='version-item'>
        <div className='t-d-gray content-3'>Version</div>
        {modalLink}
      </div>
    );
  }
}

const mapStateToProps = (state, ownProps) => {
  let wfModuleIdx;
  for (let i = 0; i < state.workflow.wf_modules.length; i++) {
    if (state.workflow.wf_modules[i].id === ownProps.wfModuleId) {
      wfModuleIdx = i;
      break;
    }
  }
  if (typeof wfModuleIdx === 'undefined') return;
  return {
    notifications: state.workflow.wf_modules[wfModuleIdx].notifications,
    versions: state.workflow.wf_modules[wfModuleIdx].versions
  }
};

const mapDispatchToProps = {
  markDataVersionsReadAction: Actions.markDataVersionsReadAction,
  updateWfModuleAction: Actions.updateWfModuleAction,
  setDataVersionAction: Actions.setDataVersionAction
};

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(DataVersionSelect);

export {DataVersionSelect as DataVersionSelectTest}


DataVersionSelect.propTypes = {
  wfModuleId:           PropTypes.number.isRequired,
  revision:             PropTypes.number.isRequired,
  api:                  PropTypes.object.isRequired,
  setClickNotification: PropTypes.func.isRequired,
  notifications:        PropTypes.bool,
  testing:              PropTypes.bool            // for testing only
};
