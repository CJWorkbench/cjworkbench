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
    return nextProps.moduleName !== this.props.moduleName;
  }

  render() {
    return (
      <div className='wf-card mx-auto' ref={this.setModuleRef}>
        <div className='output-bar-container'>
          <StatusBar status="busy" isSelected={this.props.isSelected}/>
        </div>
        <div className='card-block p-0'>
          <div className='module-card-info'>
            <div className='module-card-header'>
              <div className='module-header-content'>
                <div className='d-flex justify-content-start align-items-center'>
                  <div className={'icon-' + this.props.moduleIcon + ' WFmodule-icon mr-2'} />
                  <div className='t-d-gray WFmodule-name'>{this.props.moduleName}</div>
                </div>
              </div>
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