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
import AddNotificationButtonClosed from './AddNotificationButtonClosed';


export default class ModuleLibraryClosed extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      showArrow: false
    };
    this.toggleArrow = this.toggleArrow.bind(this);
  }

  toggleArrow() {
    if (!this.props.isReadOnly) this.setState({showArrow: !this.state.showArrow});
  }

  render() {
    var arrow = (this.state.showArrow)
      ? <div className='icon-sort-right-vl-gray'/>
      : <div className="logo">
          <img src="/static/images/logo.png" width="21"/>
        </div>

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
        />;

        <AddNotificationButtonClosed setOpenCategory={this.props.setOpenCategory} />

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
