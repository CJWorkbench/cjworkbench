import React from 'react';
import Autosuggest from 'react-autosuggest';
import PropTypes from 'prop-types'

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
      <div className='d-flex align-items-center'>
        <span className={'ml-icon-search icon-' + suggestion.icon}></span>
        <span className='mt-1 content-3'><strong>{suggestion.name}</strong></span>
      </div>
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
      onChange: this.onChange
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
  addModule: PropTypes.func.isRequired,
  items: PropTypes.array.isRequired,
  workflow: PropTypes.object.isRequired
};
