import React from 'react'
import WfModuleContextMenu  from './WfModuleContextMenu'
import { shallow } from 'enzyme'

it('WfModuleContextMenu renders correctly', () => {
  const wrapper = shallow(
    <WfModuleContextMenu 
        removeModule={ () => {} } 
        stopProp={ () => {} }
        id={1}
        className="menu-test-class"
    />);
  expect(wrapper).toMatchSnapshot();
});





