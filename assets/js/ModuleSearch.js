/**
* Search field that returns modules matching text input.
*
*/

import React from 'react';
import Autosuggest from 'react-autosuggest';
import { getEmptyImage } from 'react-dnd-html5-backend';
import PropTypes from 'prop-types'
import { DragSource } from 'react-dnd';
import { connect } from 'react-redux'
import lessonSelector from './lessons/lessonSelector'

const spec = {
  beginDrag(props) {
    return {
      type: 'module',
      index: false,
      id: props.id,
      name: props.name,
      icon: props.icon,
      insert: true,
    }
  },
  endDrag(props, monitor) {
    if (monitor.didDrop()) {
      const result = monitor.getDropResult();
      props.dropModule(
        result.source.id,
        result.source.target,
        {
          name: result.source.name,
          icon: result.source.icon,
        }
      );
    }
  }
}

function collect(connect, monitor) {
  return {
    connectDragSource: connect.dragSource(),
    connectDragPreview: connect.dragPreview(),
    isDragging: monitor.isDragging()
  }
}

function groupModules(items) {
  const ret = []
  const temp = {}

  items.forEach(item => {
    if (temp[item.category]) {
      temp[item.category].push(item)
    } else {
      const obj = { title: item.category, modules: [ item ] }
      temp[item.category] = obj.modules
      ret.push(obj)
    }
  })

  return ret
}

class ModuleSearchResult extends React.Component {
  componentDidMount() {
    this.props.connectDragPreview(getEmptyImage(), {
			// IE fallback: specify that we'd rather screenshot the node
			// when it already knows it's being dragged so we can hide it with CSS.
			captureDraggingState: true,
		})
  }

  render() {
    const className = `module-search-result ${this.props.isLessonHighlight ? 'lesson-highlight' : ''} react-autosuggest__suggestion-inner`

    return this.props.connectDragSource(
      <div className={className} data-module-name={this.props.name}>
        <div className='suggest-handle'>
          <i className='icon-grip'></i>
        </div>
        <div className='d-flex align-items-center'>
          <i className={'ml-icon-search ml-icon-container icon-' + this.props.icon}></i>
          <span className='content-5 ml-module-name'>{this.props.name}</span>
        </div>
      </div>
    )
  }
}

const DraggableModuleSearchResult = DragSource('module', spec, collect)(ModuleSearchResult)

export class ModuleSearch extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      value: '',
      suggestions: [],
    }
    this.onChange = this.onChange.bind(this);
    this.onSuggestionsClearRequested = this.onSuggestionsClearRequested.bind(this);
    this.onSuggestionsFetchRequested = this.onSuggestionsFetchRequested.bind(this);
    this.renderSectionTitle = this.renderSectionTitle.bind(this);
    this.renderSuggestion = this.renderSuggestion.bind(this);
    this.getSuggestionValue = this.getSuggestionValue.bind(this);
    this.getSectionSuggestions = this.getSectionSuggestions.bind(this);
    this.onSuggestionSelected = this.onSuggestionSelected.bind(this);
    this.clearSearchField = this.clearSearchField.bind(this);
  }

  escapeRegexCharacters (str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  onChange (event, { newValue, method }) {
    this.setState({
      value: newValue
    });
  }

  onSuggestionsFetchRequested ({ value }) {
    const suggestions = this.getSuggestions(value)
    this.setState({ suggestions })
  }

  // Autosuggest will call this function every time you need to clear suggestions.
  onSuggestionsClearRequested () {
    this.setState({
      suggestions: []
    });
  }

  renderSectionTitle (section) {
    return (
      <div className="d-flex title justfy-content-center">
        {section.title}
      </div>
    );
  }

  getSuggestions (value) {
    const escapedValue = this.escapeRegexCharacters(value.trim());

    if (escapedValue === '') {
      return [];
    }

    const regex = new RegExp(escapedValue, 'i');
    const foundModules = this.props.modules.filter(m => regex.test(m.name))

    return groupModules(foundModules)
  }

  renderSuggestion(suggestion) {
    const { id, icon, name } = suggestion
    return (
      <DraggableModuleSearchResult
        dropModule={this.props.dropModule}
        id={id}
        icon={icon}
        name={name}
        isLessonHighlight={this.props.isLessonHighlightForModuleName(name)}
        />
    )
  }

  getSuggestionValue (suggestion) {
    return suggestion.name
  }

  getSectionSuggestions (section) {
    return section.modules
  }

  onSuggestionSelected (event, { suggestion }) {
    this.props.addModule(suggestion.id);
    this.setState({value: ''});
  }

  clearSearchField() {
    this.setState({value: ''});
    // focus on search field by targeting element nested inside imported component
    this.textInput.childNodes[0].childNodes[0].focus();
  }

  render () {
    const { value, suggestions } = this.state;
    const inputProps = {
      placeholder: 'Modules',
      value,
      onChange: this.onChange,
      autoFocus: true
    };
    var closeIcon = null;
    if (this.state.value != '') {
      closeIcon = <div className='icon-close-white mr-4' onClick={this.clearSearchField}></div>
    }

    const lessonHighlightClassName = this.props.isLessonHighlight ? ' lesson-highlight' : ''
    const className = `module-search d-flex align-items-center ML-search-field${lessonHighlightClassName}`

    return (
      <div className={className}>
        <div className='icon-search-white ml-icon-search ml-4'></div>
        <div
          // can not set ref on imported component, so anchoring to parent div
          ref={input => this.textInput = input}
        >
          <Autosuggest
            multiSection={true}
            suggestions={suggestions}
            alwaysRenderSuggestions={this.props.alwaysRenderSuggestions}
            onSuggestionsFetchRequested={this.onSuggestionsFetchRequested}
            onSuggestionsClearRequested={this.onSuggestionsClearRequested}
            getSuggestionValue={this.getSuggestionValue}
            renderSuggestion={this.renderSuggestion}
            renderSectionTitle={this.renderSectionTitle}
            getSectionSuggestions={this.getSectionSuggestions}
            inputProps={inputProps}
            onSuggestionSelected={this.onSuggestionSelected}
          />
        </div>
        <div className='ML-search--close'>
          {closeIcon}
        </div>
      </div>
    )
  }
}

ModuleSearch.propTypes = {
  addModule:  PropTypes.func.isRequired,
  modules:    PropTypes.array.isRequired,
  workflow:   PropTypes.object.isRequired,
  isLessonHighlight: PropTypes.bool.isRequired,
  isLessonHighlightForModuleName: PropTypes.func.isRequired,
  alwaysRenderSuggestions: PropTypes.bool, // useful in testing
}

const mapStateToProps = (state) => {
  const { testHighlight } = lessonSelector(state)
  return {
    isLessonHighlight: testHighlight({ type: 'ModuleSearch' }),
    isLessonHighlightForModuleName: (name) => testHighlight({ type: 'MlModule', name: name }),
  }
}

export default connect(
  mapStateToProps,
  null
)(ModuleSearch)
