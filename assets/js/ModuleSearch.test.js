import React from 'react'
import ModuleSearch  from './ModuleSearch'
import { shallow } from 'enzyme'

describe('ModuleSearch', () => {

  var wrapper;  

  beforeEach(() => wrapper = shallow(
    <ModuleSearch
      addModule={ () => {} } 
      items={[]} 
      workflow={{}}
    />
  ));

  it('Renders', () => { 
    expect(wrapper).toMatchSnapshot();
  });
    
});

