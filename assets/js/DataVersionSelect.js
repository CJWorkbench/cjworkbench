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
      versions: []
    };
    this.toggleModal = this.toggleModal.bind(this);
    this.toggleDropdown = this.toggleDropdown.bind(this);    
  }

  toggleModal() {
    this.setState({ modalOpen: !this.state.modalOpen });
  }

  toggleDropdown() {
    this.setState({ dropdownOpen: !this.state.dropdownOpen });
  }

  componentDidMount() {
    var _this = this;

    var wf_module_id =  _this.props.wf_module_id;

    console.log('WF module ID: ' + wf_module_id);

    fetch('/api/wfmodules/' + wf_module_id + '/dataversions', {credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        console.log('Versions state returned: ' + JSON.stringify(json));
        _this.setState({versions: json})
      })
  }


  render() {

    return (
      <span className="ml-2">
        <Button color='secondary' onClick={this.toggleModal}>Change Data Versions</Button>
        <Modal isOpen={this.state.modalOpen} toggle={this.toggleModal} className={this.props.className}>
          <ModalHeader toggle={this.toggleModal}>Dataset Versions</ModalHeader>
          <ModalBody>
            <div className='scolling-list'>
              {this.state.versions.map( listValue => {
                return (
                    <div key={listValue.date}>
                      <div>Date: {dateFormat(listValue.date, "mmmm d yyyy - HH:MM TT")} UTC</div>
                      <div>Active: {listValue.selected ? 'YES' : 'NO'}</div>
                      <div>-------------------</div>
                    </div>
                );
              })}
            </div>
          </ModalBody>
          <ModalFooter>
            {/*Currently this button only closes the Modal window, does not change version*/}
            <Button color='secondary' onClick={this.toggleModal}>Apply</Button>
          </ModalFooter>
        </Modal>
      </span>
    );
  }

}

DataVersionSelect.propTypes = {
  wf_module_id:     PropTypes.number
};
