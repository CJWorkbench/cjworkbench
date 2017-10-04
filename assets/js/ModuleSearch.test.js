import React from 'react'
import ModuleSearch  from './ModuleSearch'
import { mount } from 'enzyme'

describe('ModuleSearch', () => {

  var wrapper;  
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

  it('Renders', () => { 
    expect(wrapper).toMatchSnapshot(); // 1    
  });

  // FAILING: how can we get State to load from the props?
  // it('Loads modules from props ', (done) => { 
    
  //   // wait modules to load from props
  //   setImmediate( () => {
  //     expect(wrapper).toMatchSnapshot(); // 2
        
  //     // FAILS
  //     // ??? why has State not loaded up the modules from props ??? 
  //     expect(wrapper.state().modules.length).toBe(2);      

  //     expect(wrapper.state().modules[0].title).toEqual("Add data");
  //     expect(wrapper.state().modules[1].title).toEqual("Filter");
      
  //     done();
  //   });
  // });

  // TODO:
  // it('Finds a suggestion matching search input', (done) => { 
  //   expect(true).toBe(true);
  //   // set immediate to load

  //   // enter value to text field

  //   // 
  // });

  // TODO: 
  // it('Loads selected module to workflow', () => { 
  //   expect(true).toBe(true);
  // });
    
});

