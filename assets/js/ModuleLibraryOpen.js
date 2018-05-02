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
import AddNotificationButtonOpen from './AddNotificationButtonOpen';


export default class ModuleLibraryOpen extends React.Component {
  constructor(props) {
    super(props);
    this.state = {};
    this.handleClick = this.handleClick.bind(this);
  }

  // Clicking on left arrow in header will collapse all categories and switch to closed library
  handleClick() {
    this.props.setOpenCategory(null);
    this.props.toggleLibrary();
  }

  render() {

    return (
        <div className='module-library--open'>
        <div className='library-header'>
          <div className="d-flex align-items-center">
            <a href="/workflows" className="brand--ML">
              <img src="/static/images/logo.svg" width="21"/>
              <div className='logo-2 ml-2 t-white'>Workbench</div>
            </a>
            <div className='close-open-toggle' onClick={this.handleClick}>
              <div className='icon-sort-left-vl-gray ml-4 mt-1'></div>
            </div>
          </div>

          <ModuleSearch addModule={this.props.addModule}
                        dropModule={this.props.dropModule}
                        items={this.props.items}
                        workflow={this.props.workflow} />
        </div>
        <div className="ML--module-list">
          <ModuleCategories
            openCategory={this.props.openCategory}
            setOpenCategory={this.props.setOpenCategory}
            libraryOpen={true}
            isReadOnly={this.props.isReadOnly}
            addModule={this.props.addModule}
            dropModule={this.props.dropModule}
            items={this.props.items}
          />;
        </div>
        <div className="ml-divider"></div>
          <AddNotificationButtonOpen/>
        <div className="ml-divider"></div>

        <ImportModuleFromGitHub
          moduleAdded={this.props.moduleAdded}
          libraryOpen={true}
          api={this.props.api}
          isReadOnly={this.props.isReadOnly}
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
