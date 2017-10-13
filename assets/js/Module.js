/**
 * A component that holds a single module that is then contained within the
 * Module Library.
 * The render function here will drive the "card" of each module within
 * the library.
 */

import React from 'react'
import PropTypes from 'prop-types'
import { CardBlock, Card } from 'reactstrap';

export default class Module extends React.Component {
  constructor(props) {
    super(props);
    this.itemClick = this.itemClick.bind(this);
//    this.addModule = this.props.addModule.bind(this);
  }

  itemClick(evt) {
    this.props.addModule(this.props.id);
    // Toggle temporarily disabled
    // this.workflow.toggleModuleLibrary();
  }

  render() {
    var moduleName = this.props.name;
    var icon = 'icon-' + this.props.icon + ' ml-icon';

    return (
      // TODO: remove inline styles
      <div className='card' style={{'borderRadius': 0, 'border': 0}}>
        <div className='' onClick={this.itemClick} >
          <div className='second-level d-flex flex-row align-items-center'>
            <div className='ml-icon-container'>
              <div className={icon}></div>
            </div>
            <div>
              <div className='content-5 ml-module-name'>{moduleName}</div>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

Module.propTypes = {
  id:         PropTypes.number.isRequired,
  name:       PropTypes.string.isRequired,
  icon:       PropTypes.string.isRequired,
  addModule:  PropTypes.func,
//  workflow:   PropTypes.object
};
