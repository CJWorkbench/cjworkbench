import React from 'react'
import { WorkflowListNavBar, WorkflowNavBar } from './navbar'
import { shallow } from 'enzyme'


describe('NavBar', () => {

  it('WorkflowListNavBar renders correctly', () => {
    var wrapper = shallow(
      <WorkflowListNavBar />
    );
    expect(wrapper).toMatchSnapshot();
  });

  it('WorkflowNavBar renders correctly', () => {
    var wrapper = shallow(
      <WorkflowNavBar 
        isReadOnly={false}
        workflowId={1} 
        api={{}}
      />
    );
    expect(wrapper).toMatchSnapshot();
  });

});
