// UI for a single module within a workflow

import React from 'react'


class WfParameter extends React.Component {

  render() {
    var type = this.props.p.type;
    var name = this.props.p.name;
    switch (type) {
      case 'string':
        return (
          <div>
            <div>{name}:</div>
            <textarea className='wfmoduleStringInput' rows='1' defaultValue={this.props.p.def_string} />
          </div>
        );

      case 'number':
        return (
          <div>
            <div>{name}:</div>
            <textarea className='wfmoduleNumberInput' rows='1' defaultValue={this.props.p.def_number} />
          </div>
        );

      case 'text':
        return (
          <div>
            <div>{name}:</div>
            <textarea className='wfmoduleTextInput' rows='4' defaultValue={this.props.p.def_text} />
          </div>
        );
    }
  }
}

export default class WfModule extends React.Component {

  render() {
    var module = this.props['data-module'];
    var params = module.parameter_specs.map((ps, i) => { return <WfParameter p={ps} key={i} /> } )

    return (
      <div {...this.props} className="module-li">
        <h1>{module.name}</h1>
        {params}
      </div>
    ); 
  } 
}
