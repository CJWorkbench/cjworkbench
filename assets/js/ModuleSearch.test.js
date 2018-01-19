/**
 * Testing Stories:
 * -Renders a search bar
 * -Search bar will render suggestions of modules matching input
 * 
 */

import React from 'react'
import ModuleSearch  from './ModuleSearch'
import { mount } from 'enzyme'

describe('ModuleSearch', () => {

  var wrapper;  
  var searchField;
  var addModule = () => {};
  var items = [
    {
      "id":4,
      "name":"Load from Enigma",
      "category":"Add data",
      "description":"Connect a dataset from Enigma's collection via URL.",
      "link":"",
      "author":"Workbench",
      "icon":"url"
    },
    {
      "id":10,
      "name":"Filter by Text",
      "category":"Filter",
      "description":"Filter rows by matching text in specific columns.",
      "link":"",
      "author":"Workbench",
      "icon":"filter"
    }
  ];
  var workflow = {
    "id":15,
    "name":"What a workflow!"
  };

  beforeEach(() => wrapper = mount(
    <ModuleSearch
      addModule={addModule} 
      items={items} 
      workflow={workflow}
    />
  ));
  beforeEach(() => searchField = wrapper.find('.react-autosuggest__input'));    

  it('Renders search bar', () => { 
    expect(wrapper).toMatchSnapshot(); // 1    
  });

  it('Loads modules from props ', (done) => { 
    
    // wait modules to load from props
    setImmediate( () => {
      expect(wrapper).toMatchSnapshot(); 
        
      expect(wrapper.state().modules.length).toBe(2);      

      expect(wrapper.state().modules[0].title).toEqual("Add data");
      expect(wrapper.state().modules[1].title).toEqual("Filter");
      
      done();
    });
  });

  it('Finds a suggestion matching search input', (done) => { 
    // wait modules to load from props
    setImmediate( () => {
      // Search field is focused by default,
      //  enter value to text field
      searchField.simulate('change', {target: {value: 'a'}});
      expect(wrapper).toMatchSnapshot();      
      // check for presence of suggestion
      expect(wrapper.state().suggestions.length).toEqual(1);              
      expect(wrapper.state().suggestions[0].modules[0].name).toEqual("Load from Enigma");      

      done();
    });
  });
    
});

