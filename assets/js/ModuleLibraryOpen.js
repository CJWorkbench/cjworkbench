/**
 * Full version of the <ModuleLibrary>. 
 * 
 * Renders a wide menu, with <ModuleSearch>, <ModuleCategories>, <AddNotificationButton>, 
 *    and <ImportModuleFromGitHub> components, and toggle arrow to Closed version.
 */

 import PropTypes from 'prop-types';
import React from 'react';
import ModuleCategories from './ModuleCategories';
import ImportModuleFromGitHub from './ImportModuleFromGitHub';
import ModuleSearch from './ModuleSearch';
import AddNotificationButton from './AddNotificationButton';


export default class ModuleLibraryOpen extends React.Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  render() {

    return (
        <div className='module-library-open'>
        <div className='library-nav-bar'>

          <div className='d-flex align-items-center flex-row mb-4'>
            <a href="/workflows" className="logo"><img src="/static/images/logo.png" width="20"/></a>
            <a href="/workflows" className='logo-2 ml-3 t-vl-gray '>Workbench</a>
            <div className='icon-sort-left-vl-gray ml-auto mt-2 close-open-toggle' onClick={this.props.toggleLibrary}></div>
          </div>

          <div className='d-flex align-items-center search-bar'>
            <div className='icon-search-white ml-icon-search ml-4'></div>
            <ModuleSearch addModule={this.props.addModule}
                          dropModule={this.props.dropModule}
                          items={this.props.items}
                          workflow={this.props.workflow} />
          </div>
        </div>

        <ModuleCategories
          openCategory={this.props.openCategory} 
          setOpenCategory={this.props.setOpenCategory}
          libraryOpen={true}
          isReadOnly={this.props.isReadOnly}            
          addModule={this.props.addModule}
          dropModule={this.props.dropModule}
          items={this.props.items}
        />;

        <div className="ml-divider"></div>

        <AddNotificationButton libraryOpen={true}/>

        <div className="ml-divider"></div>

        <ImportModuleFromGitHub 
          moduleAdded={this.props.moduleAdded} 
          libraryOpen={true}
          api={this.props.api}
        />
      </div>
    )
  }
}

ModuleLibraryOpen.propTypes = {
  workflow:         PropTypes.object.isRequired,
  api:              PropTypes.object.isRequired,
  openCategory:     PropTypes.string,
  addModule:        PropTypes.func.isRequired,
  dropModule:       PropTypes.func.isRequired,
  items:            PropTypes.array.isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  libraryOpen:      PropTypes.bool.isRequired,
  isReadOnly:       PropTypes.bool.isRequired,
  moduleAdded:      PropTypes.func.isRequired,
  toggleLibrary:    PropTypes.func.isRequired,
};

