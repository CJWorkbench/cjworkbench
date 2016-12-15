// UI for a single module within a workflow

import React from 'react'


class WfParameter extends React.Component {

  render() {
    var type = this.props.p.parameter_spec.type;
    var name = this.props.p.parameter_spec.name;
    switch (type) {
      case 'string':
        return (
          <div>
            <div>{name}:</div>
            <textarea className='wfmoduleStringInput' rows='1' defaultValue={this.props.p.string} />
          </div>
        );

      case 'number':
        return (
          <div>
            <div>{name}:</div>
            <textarea className='wfmoduleNumberInput' rows='1' defaultValue={this.props.p.number} />
          </div>
        );

      case 'text':
        return (
          <div>
            <div>{name}:</div>
            <textarea className='wfmoduleTextInput' rows='4' defaultValue={this.props.p.text} />
          </div>
        );
    }
  }
}

export default class WfModule extends React.Component {

  render() {
    var module = this.props['data-module'];
    var params= this.props['data-params'];
    var paramdivs = params.map((ps, i) => { return <WfParameter p={ps} key={i} /> } )

    return (
      <div {...this.props} className="module-li">
        <h1>{module.name}</h1>
        {paramdivs}
      </div>
    ); 
  } 
}
