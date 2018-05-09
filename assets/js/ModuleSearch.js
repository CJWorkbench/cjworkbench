/**
* Search field that returns modules matching text input.
*
*/

import React from 'react';
import Autosuggest from 'react-autosuggest';
import PropTypes from 'prop-types'
import { DragSource } from 'react-dnd';
import {logEvent} from "./utils";
import { connect } from 'react-redux'
import { stateHasLessonHighlight } from './util/LessonHighlight'

const spec = {
  beginDrag(props, monitor, component) {
    return {
      index: false,
      id: props.id,
      insert: true,
    }
  },
  endDrag(props, monitor, component) {
    if (monitor.didDrop()) {
      const result = monitor.getDropResult();
      props.dropModule(result.source.id, result.source.index);
    }
  }
}

function collect(connect, monitor) {
  return {
    connectDragSource: connect.dragSource(),
    isDragging: monitor.isDragging()
  }
}

class ModuleSearchResult extends React.Component {
  render() {
    return this.props.connectDragSource(
      <div className='react-autosuggest__suggestion-inner'>
        <div className='suggest-handle'>
          <div className='icon-grip'></div>
        </div>
        <div className='d-flex align-items-center'>
          <span className={'ml-icon-search ml-icon-container icon-' + this.props.icon}></span>
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
      modules: []
    };
    this.onChange = this.onChange.bind(this);
    this.escapeRegexCharacters = this.escapeRegexCharacters.bind(this);
    this.onSuggestionsClearRequested = this.onSuggestionsClearRequested.bind(this);
    this.onSuggestionsFetchRequested = this.onSuggestionsFetchRequested.bind(this);
    this.renderSectionTitle = this.renderSectionTitle.bind(this);
    this.formatModules = this.formatModules.bind(this);
    this.getSuggestions = this.getSuggestions.bind(this);
    this.renderSuggestion = this.renderSuggestion.bind(this);
    this.getSuggestionValue = this.getSuggestionValue.bind(this);
    this.getSectionSuggestions = this.getSectionSuggestions.bind(this);
    this.onSuggestionSelected = this.onSuggestionSelected.bind(this);
    this.onBlur = this.onBlur.bind(this);
    this.clearSearchField = this.clearSearchField.bind(this);

    this.lastLoggedQuery = ''; // debounce query logging
  }

  componentDidMount() {
    if (this.props.modules) {
      this.formatModules(this.props.modules);
    }
  }

  componentWillReceiveProps(nextProps) {
    if (this.props.modules !== nextProps.modules) {
      this.formatModules(nextProps.modules)
    }
  }

  escapeRegexCharacters (str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  formatModules(items) {
    let modules = [];
    let temp = {};

    if (items.length) {
      items.forEach(item => {
        if (temp[item.category]) {
          temp[item.category].push(item);
        } else {
          temp[item.category] = [item];
        }
      });

      for (let item in temp) {
        modules.push({title: item, modules: temp[item]});
      }
    }
    this.setState({ modules });
  }

  onChange (event, { newValue, method }) {
    this.setState({
      value: newValue
    });
  }

  onSuggestionsFetchRequested ({ value }) {
    this.setState({
      suggestions: this.getSuggestions(value)
    });
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

    return this.state.modules
      .map(section => {
        return {
          title: section.title,
          modules: section.modules.filter(module => regex.test(module.name))
        };
      })
      .filter(section => section.modules.length > 0);
  }

  renderSuggestion (suggestion) {
    return (
      <DraggableModuleSearchResult
        dropModule={this.props.dropModule}
        icon={suggestion.icon}
        name={suggestion.name}
        id={suggestion.id} />
    )
  }

  getSuggestionValue (suggestion) {
    return suggestion.name;
  }

  getSectionSuggestions (section) {
    return section.modules;
  }

  onSuggestionSelected (event, { suggestion }) {
    this.props.addModule(suggestion.id);
    this.setState({value: ''});
  }

  // When the user moves away from the search box, log the query
  onBlur() {
    var value = this.state.value;
    if (value !== '' && value != this.lastLoggedQuery) {
      logEvent('Module search', {'value': value})
      this.lastLoggedQuery = value;
    }
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

    return (
      <div className={`module-search d-flex align-items-center ML-search-field${lessonHighlightClassName}`}>
        <div className='icon-search-white ml-icon-search ml-4'></div>
        <div
          onBlur={this.onBlur}
          // can not set ref on imported component, so anchoring to parent div
          ref={input => this.textInput = input}
        >
          <Autosuggest
            multiSection={true}
            suggestions={suggestions}
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
}

const isLessonHighlight = stateHasLessonHighlight({ type: 'ModuleSearch' })
const mapStateToProps = (state) => {
  return {
    isLessonHighlight: isLessonHighlight(state),
  }
}

export default connect(
  mapStateToProps,
  null
)(ModuleSearch)
