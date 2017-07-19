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
    if (props.timezone_offset != undefined) {
      this.state.timezoneOffset = props.timezone_offset;
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

    // Convert to milliseconds, then add tz offset (which is in minutes)
    var nd = new Date(d.getTime() + (60000*this.state.timezoneOffset));

    // return time as a user-readable string
    return dateFormat(nd, "mmmm d yyyy - hh:MM TT")
  }

  toggleModal() {
    this.setState(Object.assign({}, this.state, { modalOpen: !this.state.modalOpen }));
  }

  toggleDropdown() {
    this.setState(Object.assign({}, this.state, { dropdownOpen: !this.state.dropdownOpen }));
  }

  componentDidMount() {
    var wf_module_id =  this.props.wf_module_id;

    this.props.api.getWfModuleVersions(wf_module_id)
      .then(json => {
        console.log('Versions state returned: ' + JSON.stringify(json));
        this.setState(
          Object.assign({}, this.state, {versions: json, originalSelected: json.selected})
        );
      })
  }

  setSelected(date) {
    console.log('Setting this date as selected: ' + date);
    this.setState(
      Object.assign(
        {}, 
        this.state, 
        {versions: {'versions': this.state.versions.versions, 'selected': date}}
      )
    );
  }

  changeVersions() {
    if (this.state.versions.selected !== this.state.originalSelected) {
      this.props.api.setWfModuleVersion(this.props.wf_module_id, this.state.versions.selected)
      .then(() => {
        console.log('changing originalSelected to ' + this.state.versions.selected);
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
      <div className='version-item'>
        <div className='info-blue mb-2' onClick={this.toggleModal}>Current Version</div>

        <div className='open-modal'>
            {this.state.originalSelected != '' ? this.formatDate(this.state.originalSelected) : ''}  
           {/* {this.state.originalSelected}  */}
           
        </div>        
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} >
          <ModalHeader toggle={this.toggleModal} >
            <div className=''>Dataset Versions</div>
          </ModalHeader>
          <ModalBody>
            <div className='scolling-list'>
              {this.state.versions.versions.map( date => {
                return (
                  <div 
                    key={date} 
                    className={(date == this.state.versions.selected) ? 'version-active ' : 'version-disabled'}
                    onClick={() => this.setSelected(date)}
                  >
                    <div className={(date == this.state.versions.selected) ? 'line-item-active list-test-class' : 'line-item-disabled list-test-class'}>
                      { this.formatDate(date) }
                    </div>
                  </div>
                );
              })}
            </div>
          </ModalBody>
          <ModalFooter>
            <Button className='button-blue' onClick={this.toggleModal}>Cancel</Button>    
            <Button className='button-blue' onClick={this.changeVersions}>OK</Button>                    
          </ModalFooter>
        </Modal>
      </div>
    );
  }
}

DataVersionSelect.propTypes = {
  wf_module_id:    PropTypes.number.isRequired,
  api:             PropTypes.object.isRequired,
  timezone_offset: PropTypes.number
};
