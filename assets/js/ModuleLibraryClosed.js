/**
 * Collapsed version of the <ModuleLibrary>. 
 * 
 *  Renders a narrow menu, with <ModuleCategories>, <AddNotificationButton>, 
 *    and <ImportModuleFromGitHub> components, and toggle arrow to Clossed version.
 */

import PropTypes from 'prop-types';
import React from 'react';
import ModuleCategories from './ModuleCategories';
import ImportModuleFromGitHub from './ImportModuleFromGitHub';
import AddNotificationButton from './AddNotificationButton';


export default class ModuleLibraryClosed extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      showArrow: false
    };
    this.showArrow = this.showArrow.bind(this);
    this.hideArrow = this.hideArrow.bind(this);
  }

  showArrow() {
    if (!this.props.isReadOnly) this.setState({showArrow: true});
  }

  hideArrow() {
    if (!this.props.isReadOnly) this.setState({showArrow: false});
  }

  render() {

    return (
      <div className='module-library-closed'>
      
        <div className="expand-lib" onMouseEnter={this.showArrow} onMouseLeave={this.hideArrow}>
          <div className="expand-lib-button d-flex">
            <div className="logo" style={{ display: this.state.showArrow ? 'none' : 'block' }}>
              <img src="/static/images/logo.png" width="20"/>
            </div>
            <div
              className='icon-sort-right-vl-gray close-open-toggle'
              onClick={this.props.openLibrary}
              style={{ display: this.state.showArrow ? 'block' : 'none' }}>
            </div>
          </div>
        </div>

        <div className='card' onClick={this.props.openLibrary}>
          <div className='first-level'>
            <div className='icon-search-white ml-icon-search text-center mt-3'></div>
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
        />;

        <AddNotificationButton libraryOpen={false}/>

        <ImportModuleFromGitHub 
          moduleAdded={this.props.moduleAdded} 
          libraryOpen={false}
          api={this.props.api}
        />          

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

