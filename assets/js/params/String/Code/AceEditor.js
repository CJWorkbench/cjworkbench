import { createRef, PureComponent } from 'react'
import PropTypes from 'prop-types'
import AceEditor from 'react-ace/lib/ace'
import memoize from 'memoize-one'
import { Trans } from '@lingui/macro'
import { QuickFixPropTypes } from '../../../WorkflowEditor/step/QuickFix'

import 'ace-builds/src-noconflict/mode-python'
import 'ace-builds/src-noconflict/mode-sql'
import 'ace-builds/src-noconflict/theme-xcode'

// Globals -- so each render(), they're equal according to ===
const EditorProps = {
  // $blockScrolling fixes a console.warn() we'd otherwise see
  $blockScrolling: Infinity
}

function SyntaxHelp ({ syntax }) {
  switch (syntax) {
    case 'python':
      return (
        <Trans
          id='js.params.Custom.Code.AceEditor.help'
          comment='The tags <3>, <6>, and <8> are URLs. The rest are code formatting. Please keep code and names of libraries untranslated.'
        >
          Define a <kbd>process(table)</kbd> function that accepts a{' '}
          <kbd>pd.DataFrame</kbd> and returns a <kbd>pd.DataFrame</kbd>. You may
          use the{' '}
          <a
            target='_blank'
            rel='noopener noreferrer'
            href='https://docs.python.org/3/library/math.html'
          >
            <kbd>math</kbd>
          </a>
          , <kbd>pd</kbd> (
          <a
            target='_blank'
            rel='noopener noreferrer'
            href='https://pandas.pydata.org/pandas-docs/stable/api.html#dataframe'
          >
            Pandas
          </a>
          ) and <kbd>np</kbd> (
          <a
            target='_blank'
            rel='noopener noreferrer'
            href='https://docs.scipy.org/doc/numpy/reference/routines.html'
          >
            Numpy
          </a>
          ) modules.
        </Trans>
      )
    case 'sql':
      return (
        <Trans id='js.params.Custom.Code.AceEditor.help.sql'>
          Write an SQL <kbd>SELECT</kbd> query that reads from the{' '}
          <kbd>"input"</kbd> table.
        </Trans>
      )
  }
}

export default class WorkbenchAceEditor extends PureComponent {
  static propTypes = {
    // When isZenMode changes, we'll call componentDidUpdate()
    isZenMode: PropTypes.bool.isRequired,
    stepOutputErrors: PropTypes.arrayOf(
      PropTypes.shape({
        message: PropTypes.string.isRequired,
        quickFixes: PropTypes.arrayOf(PropTypes.shape(QuickFixPropTypes))
          .isRequired
      }).isRequired
    ).isRequired, // may (hopefully) be empty
    name: PropTypes.string.isRequired,
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired // func(value) => undefined
  }

  state = {
    // We'll modify width and height to px values, causing a change, so
    // AceEditor will know to recalculate things (like line wraps).
    width: '100%',
    height: '100%'
  }

  wrapperRef = createRef()

  componentDidMount () {
    this.updateSize()
  }

  componentDidUpdate (prevProps) {
    // ignore state changes, since we _cause_ them
    if (prevProps === this.props) return

    this.updateSize()
  }

  updateSize () {
    const div = this.wrapperRef.current
    if (!div) return

    // Force height to equal width
    this.setState({
      width: div.clientWidth + 'px',
      height: div.clientWidth + 'px'
    })
  }

  getAnnotations = memoize(stepOutputErrors => {
    return stepOutputErrors
      .map(error => {
        const m = /^Line (\d+): (.*)/.exec(error.message)
        if (m) {
          return {
            row: +m[1] - 1,
            type: 'error',
            text: m[2]
          }
        } else {
          return null
        }
      })
      .filter(x => x)
  })

  // Render editor
  render () {
    const {
      value,
      onChange,
      isZenMode,
      stepOutputErrors,
      placeholder,
      syntax
    } = this.props

    return (
      <div className='ace-wrapper-outer'>
        <div className='help'>
          <SyntaxHelp syntax={syntax} />
        </div>
        <div className='ace-aspect-ratio-container'>
          <div className='ace-wrapper' ref={this.wrapperRef}>
            <AceEditor
              editorProps={EditorProps}
              width={this.state.width}
              height={this.state.height}
              mode={syntax}
              placeholder={placeholder}
              theme='xcode'
              wrapEnabled
              annotations={this.getAnnotations(stepOutputErrors)}
              showGutter={isZenMode /* false hides annotations */}
              name='code-editor'
              onChange={onChange}
              value={value}
            />
          </div>
        </div>
      </div>
    )
  }
}
