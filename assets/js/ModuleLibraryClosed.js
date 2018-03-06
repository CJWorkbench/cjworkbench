/**
 * Collapsed version of the <ModuleLibrary>.
 *
 *  Renders a narrow menu, with <ModuleCategories>, <AddNotificationButton>,
 *    and <ImportModuleFromGitHub> components, and toggle arrow to Clossed version.
 */

import PropTypes from 'prop-types';
import React from 'react';
import {Modal, ModalHeader, ModalBody, ModalFooter} from 'reactstrap'
import ModuleCategories from './ModuleCategories';
import ImportModuleFromGitHub from './ImportModuleFromGitHub';
import AddNotificationButtonClosed from './AddNotificationButtonClosed';


export default class ModuleLibraryClosed extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      showArrow: false,
      signInModalOpen: false,
    };
    this.toggleArrow = this.toggleArrow.bind(this);
    this.toggleSignInModal = this.toggleSignInModal.bind(this);
  }

  toggleArrow() {
    if (!this.props.isReadOnly) 
      this.setState({showArrow: !this.state.showArrow});
  }

  toggleSignInModal() {
    if (this.props.isReadOnly) 
      this.setState({ signInModalOpen: !this.state.signInModalOpen });
  }

  renderSignInModal() {
    if (!this.state.signInModalOpen || !this.props.isReadOnly) {
      return null;
    }

    return (
      <Modal isOpen={this.state.signInModalOpen} toggle={this.toggleSignInModal} className='test-signin-modal'>
        <ModalHeader className='dialog-header modal-header d-flex align-items-center' >
          <div className='t-d-gray title-4'>SIGN IN TO EDIT</div>
          <div className='icon-close' onClick={this.toggleSignInModal}></div>
        </ModalHeader>
        <ModalBody className='dialog-body mt-4 mb-4 d-flex align-items-center'>
          <a href="/account/login" className="button-blue col-sm-3 action-button">Sign in</a>
          <div className="info-2 col-sm-9 ml-4">Log in to your account to duplicate and edit this workflow.</div>
        </ModalBody>
      </Modal>
    );
  }

  render() {
    let arrow = null;
    if (this.state.showArrow) {
      arrow = <div className='icon-sort-right-vl-gray'/>
    } else {
      arrow = <div className="logo">
                <img src="/static/images/logo.png" width="21"/>
              </div>
    }

    let signInModal = this.renderSignInModal();


    return (
      <div className='module-library--closed'>

        <div
          className="library-closed--toggle"
          onMouseEnter={this.toggleArrow}
          onMouseLeave={this.toggleArrow}
          onClick={this.props.openLibrary}
        >
          {arrow}
        </div>

        {/* If in read-only mode, clicking anywhere below header opens modal */}
        <div onClick={this.toggleSignInModal}>

          <div className='card' onClick={this.props.openLibrary}>
            <div className='closed-ML--category'>
              <div className='icon-search-white ml-icon-search'></div>
            </div>
          </div>

          <ModuleCategories
            openCategory={this.props.openCategory}
            setOpenCategory={this.props.setOpenCategory}
            libraryOpen={false}
            isReadOnly={this.props.isReadOnly}
            addModule={this.props.addModule}
            dropModule={this.props.dropModule}
            items={this.props.items}
          />

          <AddNotificationButtonClosed
            setOpenCategory={this.props.setOpenCategory}
            isReadOnly={this.props.isReadOnly}
          />

          <ImportModuleFromGitHub
            moduleAdded={this.props.moduleAdded}
            libraryOpen={false}
            api={this.props.api}
            isReadOnly={this.props.isReadOnly}
          />

          {signInModal}

        </div>

      </div>
    )
  }
}

ModuleLibraryClosed.propTypes = {
  api:              PropTypes.object.isRequired,
  openCategory:     PropTypes.string,
  addModule:        PropTypes.func.isRequired,
  dropModule:       PropTypes.func.isRequired,
  items:            PropTypes.array.isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  libraryOpen:      PropTypes.bool.isRequired,
  isReadOnly:       PropTypes.bool.isRequired,
  moduleAdded:      PropTypes.func.isRequired,
  openLibrary:      PropTypes.func.isRequired,
};
