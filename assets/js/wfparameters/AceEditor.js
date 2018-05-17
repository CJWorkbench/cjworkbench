import React from 'react';
import AceEditor from 'react-ace/lib/ace';

import 'brace/mode/python';
import 'brace/theme/tomorrow';

export default class WorkbenchAceEditor extends React.Component {
  constructor(props) {
    super(props);
    this.onChange = this.onChange.bind(this);
    this.state = {
      value: this.props.defaultValue
    }
  }

  onChange(newValue) {
    this.setState({
      value: newValue
    })
  }

  // Render editor
  render() {
    // $blockScrolling fixes a console.warn() we'd otherwise see
    return (
      <div className='parameter-margin'>
        <div className='label-margin t-d-gray content-3'>{this.props.name}</div>
        <AceEditor
          editorProps={{ $blockScrolling: Infinity }}
          width="100%"
          height="10rem"
          mode="python"
          theme="tomorrow"
          name="code-editor"
          onChange={this.onChange}
          onBlur={() => this.props.onSave(this.state.value)}
          value={this.state.value}
        />
      </div>
    );
  }
}
