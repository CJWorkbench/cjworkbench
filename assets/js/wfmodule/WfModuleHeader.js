import React from 'react';
import PropTypes from 'prop-types';
import StatusBar from './StatusBar';

export default class WfModuleHeader extends React.Component {
  constructor(props) {
    super(props);
    this.setModuleRef = this.setModuleRef.bind(this);
  }

  componentDidMount() {
    if (this.props.isSelected) {
      this.props.focusModule(this.moduleRef);
    }
  }

  setModuleRef(ref) {
    this.moduleRef = ref;
  }

  shouldComponentUpdate(nextProps) {
    // There's almost certainly a better way to do this. This gets the
    // job done but I'm sure there's a standard practice around this.
    return nextProps.moduleName !== this.props.moduleName &&
      nextProps.isSelected !== this.props.isSelected;
  }

  render() {
    return (
      <div className='wf-module--placeholder mx-auto' ref={this.setModuleRef}>
        <div className='module-content'>
            <div className='module-card-header'>
              <div className='d-flex justify-content-start align-items-center'>
                <div className={'icon-' + this.props.moduleIcon + ' WFmodule-icon t-vl-gray mr-2'} />
                <div className='t-vl-gray WFmodule-name'>{this.props.moduleName}</div>
              </div>
            </div>
        </div>
      </div>
    );
  }
}

WfModuleHeader.PropTypes = {
  isSelected: PropTypes.bool,
  moduleIcon: PropTypes.string,
  moduleName: PropTypes.string,
  focusModule: PropTypes.func
};
