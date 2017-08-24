import React from 'react'
import ModuleLibrary  from './ModuleLibrary'
import { shallow } from 'enzyme'

describe('ModuleLibrary', () => {

  var wrapper;  

  beforeEach(() => wrapper = shallow(
    <ModuleLibrary
      addModule={ () => {} }
      api={{}}
      workflow={{}} 
    />
  ));

  it('Renders - no modules', () => { 
    expect(wrapper).toMatchSnapshot();
  });
    
});

