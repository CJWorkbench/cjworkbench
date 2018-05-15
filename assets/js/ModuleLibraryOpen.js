/**
 * Full version of the <ModuleLibrary>.
 *
 * Renders a wide menu, with <ModuleSearch>, <ModuleCategories>, <AddNotificationButton>,
 *    and <ImportModuleFromGitHub> components, and toggle arrow to Closed version.
 */

import PropTypes from 'prop-types';
import React from 'react';
import ModuleCategories from './ModuleCategories';
import ModuleSearch from './ModuleSearch'
import AddNotificationButtonOpen from './AddNotificationButtonOpen'

export default class ModuleLibraryOpen extends React.Component {
  constructor(props) {
    super(props)
    this.handleClick = this.handleClick.bind(this)
  }

  // Clicking on left arrow in header will collapse all categories and switch to closed library
  handleClick() {
    this.props.setOpenCategory(null)
    this.props.toggleLibrary()
  }

  render() {
    return (
      <div className='module-library module-library--open'>
        <div className="ML-header">
          <a href="/workflows" className="brand--ML">
            <img src="/static/images/logo.svg" width="21"/>
            <div className='logo-2 ml-2'>Workbench</div>
          </a>
          <div className='ML-toggle' onClick={this.handleClick}>
            <div className='icon-sort-left-vl-gray ml-4 mt-1'></div>
          </div>
        </div>
        <div className='ML-list--container'>
          <div className='ML-search--container'>
            <ModuleSearch
              addModule={this.props.addModule}
              dropModule={this.props.dropModule}
              modules={this.props.modules}
              workflow={this.props.workflow}
              />
          </div>
          <div className="ML--module-list">
            <ModuleCategories
              openCategory={this.props.openCategory}
              setOpenCategory={this.props.setOpenCategory}
              libraryOpen={true}
              isReadOnly={this.props.isReadOnly}
              addModule={this.props.addModule}
              dropModule={this.props.dropModule}
              modules={this.props.modules}
            />
          </div>
        </div>
        <div className="mb-3"></div>
        <AddNotificationButtonOpen/>
        <div className="ml-divider"></div>

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
  modules:          PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    category: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
  })).isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  libraryOpen:      PropTypes.bool.isRequired,
  isReadOnly:       PropTypes.bool.isRequired,
  toggleLibrary:    PropTypes.func.isRequired,
}
