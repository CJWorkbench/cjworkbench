import React from 'react'
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import { Form, FormGroup, Label, Input } from 'reactstrap'
import { Dropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import { csrfToken } from './utils'
import dateFormat from 'dateformat'
import PropTypes from 'prop-types'



export default class DataVersionSelect extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      modalOpen: false,
      dropdownOpen: false,
      versions: {versions: [], selected: ''},
      originalSelected: ''
    };

    // Allow props to specify a conversion from browser time to displayed time, so tests can run in UTC (not test machine tz)
    if (props.timezoneOffset != undefined) {
      this.state.timezoneOffset = props.timezoneOffset;
    } else {
      this.state.timezoneOffset = 0; // display in browser local time
    }

    this.toggleModal = this.toggleModal.bind(this);
    this.toggleDropdown = this.toggleDropdown.bind(this);
    this.setSelected = this.setSelected.bind(this);
    this.changeVersions = this.changeVersions.bind(this);
  }

  // Takes a date string, interpreted as UTC, and produce a string for user display in user tz
  formatDate(datestr) {

    // interpret date string as UTC always (comes from server this way)
    var d = new Date(datestr + 'UTC');

    // check if we have a valid date
    if (isNaN(d.getTime())) return null;

    // Convert to milliseconds, then add tz offset (which is in minutes)
    var nd = new Date(d.getTime() + (60000*this.state.timezoneOffset));

    // return time as a user-readable string
    return dateFormat(nd, "mmmm d yyyy - hh:MM TT")
  }

  toggleModal() {
    if (!this.props.isReadOnly) {
      this.setState(Object.assign({}, this.state, { modalOpen: !this.state.modalOpen }));
    }
  }

  toggleDropdown() {
    if (this.props.isReadOnly) {
      this.setState(Object.assign({}, this.state, { dropdownOpen: !this.state.dropdownOpen }));
    }
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
    // TODO: Assign conditional render if module is open/closed: see WfModule 115
    // TODO: Refactor calculated classNames outside of Return statement

    return (
      <div className='version-item d-flex justify-content-center flex-column align-items-center'>
        <div className='t-d-gray content-3 mb-4'>Current Version</div>

        <div className='open-modal t-f-blue content-3 text-center' onClick={this.toggleModal}>
            {this.state.originalSelected != '' ? this.formatDate(this.state.originalSelected) : ''}
        </div>
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} >
          <ModalHeader toggle={this.toggleModal} >
            <div className=''>Dataset Versions</div>
          </ModalHeader>
          <ModalBody className='dialog-body'>
            <div className='scolling-list'>
              {this.state.versions.versions.map( date => {
                return (
                  <div
                    key={date}
                    className={
                      (date == this.state.versions.selected)
                        ? 'line-item-data-selected list-test-class'
                        : 'line-item-data  list-test-class'
                    }
                    onClick={() => this.setSelected(date)}
                  >
                    <span className='content-3'>{ this.formatDate(date) }</span>
                  </div>
                );
              })}
            </div>
          </ModalBody>
          <ModalFooter className='dialog-footer'>
            <div className='button-blue action-button' onClick={this.toggleModal}>Cancel</div>
            <div className='button-blue action-button' onClick={this.changeVersions}>OK</div>
          </ModalFooter>
        </Modal>
      </div>
    );
  }
}

DataVersionSelect.propTypes = {
  wfModuleId:       PropTypes.number.isRequired,
  revision:         PropTypes.number.isRequired,
  api:              PropTypes.object.isRequired,
  timezoneOffset:   PropTypes.number
};
