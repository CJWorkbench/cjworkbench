// Pick a single column
import React from 'react'
import PropTypes from 'prop-types'

export default class ColumnParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    value: PropTypes.string, // or null
    prompt: PropTypes.string, // default 'Select'
    isReadOnly: PropTypes.bool.isRequired,
    workflowRevision: PropTypes.number.isRequired,
    fetchInputColumns: PropTypes.func.isRequired, // func() => Promise[Array[String]]
    onChange: PropTypes.func.isRequired // func(colnameOrNull) => undefined
  }

  state = {
    allColumns: null,
    allColumnsFetchError: null,
    allColumnsWorkflowRevision: null,
  }

  loadInputColumns () {
    const { allColumns, allColumnsFetchError, allColumnsWorkflowRevision } = this.state
    if (allColumnsWorkflowRevision === this.props.workflowRevision) return

    this.setState({
      allColumns: null,
      allColumnsFetchError: null,
      allColumnsWorkflowRevision: this.props.workflowRevision
    })

    const setState = (state) => {
      if (!this.mounted) return
      if (this.state.allColumnsWorkflowRevision !== this.props.workflowRevision) return // race -- two concurrent fetches

      this.setState(state)
    }

    this.props.fetchInputColumns()
      .then(allColumns => setState({ allColumns }))
      .catch(allColumnsFetchError => setState({ allColumnsFetchError }))
  }

  // Load column names when first rendered
  componentDidMount () {
    this.mounted = true
    this.loadInputColumns()
  }

  componentWillUnmount () {
    this.mounted = false
  }

  componentDidUpdate(prevProps) {
    if (prevProps.workflowRevision !== this.props.workflowRevision) {
      this.loadInputColumns()
    }
  }

  onChange = (ev) => {
    this.props.onChange(ev.target.value || null)
  }

  render() {
    const { allColumns, allColumnsFetchError } = this.state
    const { prompt, value } = this.props

    let className = 'custom-select module-parameter dropdown-selector'

    const options = (allColumns || []).map(name => (
      <option key={name}>{name}</option>
    ))
    if (allColumnsFetchError !== null) {
      className += ' error'
      options.push(<option disabled className="error" key="error" value="">Error loading columns</option>)
    } else {
      // Select prompt when no column is selected, _or_ when an invalid
      // column is selected. `value || ''` is the currently-selected value.
      //
      // When a column is selected, set the prompt to '' so it is _not_
      // selected.
      const promptValue = (allColumns || []).indexOf(value) === -1 ? (value || '') : ''
      options.unshift(<option disabled className="prompt" key="prompt" value={promptValue}>{prompt || 'Select'}</option>)

      if (allColumns === null) {
        className += ' loading'
        options.push(<option disabled className="loading" key="loading" value="">Loading columns</option>)
      }
    }

    return (
      <select
        className={className}
        value={value || ''}
        onChange={this.onChange}
        name={this.props.name}
        disabled={this.props.isReadOnly}
      >
        {options}
      </select>
    )
  }
}
