/**
* Search field that returns modules matching text input.
* 
*/

import React from 'react';
import Autosuggest from 'react-autosuggest';
import PropTypes from 'prop-types'
import { DragSource } from 'react-dnd';

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
  constructor(props) {
    super(props);
  }
  render() {
    return this.props.connectDragSource(
      <div className='react-autosuggest__suggestion-inner'>
      <div className='suggest-handle'>
        <div className='icon-grip'></div>
      </div>
        <div className='d-flex align-items-center'>
          <span className={'ml-icon-search icon-' + this.props.icon}></span>
          <span className='mt-1 content-3'><strong>{this.props.name}</strong></span>
        </div>
      </div>
    )
  }
}

const DraggableModuleSearchResult = DragSource('module', spec, collect)(ModuleSearchResult)

export default class ModuleSearch extends React.Component {
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
  }

  componentDidMount() {
    if (this.props.items) {
      this.formatModules(this.props.items);
    }
  }

  componentWillReceiveProps(nextProps) {
    if (this.props.items !== nextProps.items) {
      this.formatModules(nextProps.items);
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
      <div>
        <strong>{section.title}</strong>
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
    );
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


  render () {
    const { value, suggestions } = this.state;
    const inputProps = {
      placeholder: 'Search modules',
      value,
      onChange: this.onChange,
      autoFocus: true
    };
    return (
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
    );
  }
}


ModuleSearch.propTypes = {
  addModule:  PropTypes.func.isRequired,
  items:      PropTypes.array.isRequired,
  workflow:   PropTypes.object.isRequired
};
