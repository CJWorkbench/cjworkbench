import React from 'react'
import PropTypes from 'prop-types'
import AceEditor from 'react-ace/lib/ace'
import memoize from 'memoize-one'

import 'brace/mode/python'
import 'brace/theme/tomorrow'

// Globals -- so each render(), they're equal according to ===
const EditorProps = {
  // $blockScrolling fixes a console.warn() we'd otherwise see
  $blockScrolling: Infinity
}

export default class WorkbenchAceEditor extends React.PureComponent {
  static propTypes = {
    // When isZenMode changes, we'll call componentDidUpdate()
    isZenMode: PropTypes.bool.isRequired,
    wfModuleError: PropTypes.string,
    name: PropTypes.string.isRequired,
    defaultValue: PropTypes.string.isRequired,
    save: PropTypes.func.isRequired // func(value) => undefined
  }

  constructor (props) {
    super(props)

    this.state = {
      value: this.props.defaultValue,
      // We'll modify width and height to px values, causing a change, so
      // AceEditor will know to recalculate things (like line wraps).
      width: '100%',
      height: '100%'
    }

    this.wrapperRef = React.createRef()
  }

  componentDidMount() {
    this.updateSize()
  }

  componentDidUpdate(prevProps) {
    // ignore state changes, since we _cause_ them
    if (prevProps === this.props) return

    this.updateSize()
  }

  updateSize() {
    const div = this.wrapperRef.current
    if (!div) return

    this.setState({
      width: div.clientWidth + 'px',
      height: div.clientHeight + 'px'
    })
  }

  onChange = (newValue) => {
    this.setState({
      value: newValue
    })
  }

  onBlur = () => {
    this.props.save(this.state.value)
  }

  getAnnotations = memoize(wfModuleError => {
    const m = /^Line (\d+): (.*)/.exec(wfModuleError)
    if (!m) {
      return []
    } else {
      return [
        {
          row: +m[1] - 1,
          type: 'error',
          text: m[2]
        }
      ]
    }
  })

  // Render editor
  render () {
    return (
      <div className='code-editor'>
        <div className='label-margin t-d-gray content-3'>{this.props.name}</div>
        <div className='ace-aspect-ratio-container'>
          <div className='ace-wrapper' ref={this.wrapperRef}>
            <AceEditor
              editorProps={EditorProps}
              width={this.state.width}
              height={this.state.height}
              mode='python'
              theme='tomorrow'
              wrapEnabled={true}
              annotations={this.getAnnotations(this.props.wfModuleError)}
              showGutter={this.props.isZenMode}
              name='code-editor'
              onChange={this.onChange}
              onBlur={this.onBlur}
              value={this.state.value}
            />
          </div>
        </div>
      </div>
    )
  }
}
