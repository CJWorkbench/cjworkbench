import PropTypes from 'prop-types';
import React from 'react';
import ModuleCategories from './ModuleCategories';
import ImportModuleFromGitHub from './ImportModuleFromGitHub';
import ModuleSearch from './ModuleSearch';
import AddNotificationButton from './AddNotificationButton';


/**
 * Collapsed version of the Module Library. 
 */

export default class ModuleLibraryClosed extends React.Component {
  constructor(props) {
    super(props);

    this.state = {};
  }

  render() {
    var toggleArrow = (this.props.isReadOnly)
      ? null
      : <div
          className='icon-sort-right-vl-gray ml-auto ml-3 mt-2 close-open-toggle'
          onClick={this.props.toggleLibrary}>
        </div>

    return (
      <div className='module-library-closed'>
      
        <div className="expand-lib">
          <div className="expand-lib-button d-flex">
            <div className="logo" onClick={this.props.toggleLibrary}><img src="/static/images/logo.png" width="20"/></div>
            { toggleArrow }
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

        <ImportModuleFromGitHub moduleAdded={this.props.moduleAdded} libraryOpen={false}/>          

      </div>
    )
  }
}

ModuleLibraryClosed.propTypes = {
  openCategory:     PropTypes.string,
  addModule:        PropTypes.func.isRequired,
  dropModule:       PropTypes.func.isRequired,
  items:            PropTypes.array.isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  libraryOpen:      PropTypes.bool.isRequired,
  isReadOnly:       PropTypes.bool.isRequired,
  moduleAdded:      PropTypes.func.isRequired,
  toggleLibrary:    PropTypes.func.isRequired,
  openLibrary:      PropTypes.func.isRequired,
};

