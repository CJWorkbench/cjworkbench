import React from 'react'
import WfHamburgerMenu  from './WfHamburgerMenu'
import { mount } from 'enzyme'


describe('WfHamburgerMenu', () => {
  let wrapper; // all tests must mount one
  afterEach(() => wrapper.unmount());

  it('renders logged in, non-read only', () => {
    wrapper = mount(<WfHamburgerMenu
      workflowId={1}
      api={{}}
      isReadOnly={false}
      user={{id: 100}}
    />);

    expect(wrapper).toMatchSnapshot(); // one snapshot only, in most common case

    expect(wrapper.find('a[href="/workflows"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Undo"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Redo"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Import Module"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Log Out"]')).toHaveLength(1);
  });

  it('renders logged in, read only', () => {
    wrapper = mount(<WfHamburgerMenu
      workflowId={1}
      api={{}}
      isReadOnly={true}
      user={{id: 100}}
    />);

    expect(wrapper.find('a[href="/workflows"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Undo"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Redo"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Import Module"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Log Out"]')).toHaveLength(1);
  });

  it('renders logged out, read only', () => {
    wrapper = mount(<WfHamburgerMenu
      workflowId={1}
      api={{}}
      isReadOnly={true}
      user={undefined}
    />);

    expect(wrapper.find('a[href="https://workbenchdata.com"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Undo"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Redo"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Import Module"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Log In"]')).toHaveLength(1);
  });


  it('renders without a workflowId', () => {
    // this happens on Workflow list page
    wrapper = mount(<WfHamburgerMenu
      api={{}}
      isReadOnly={true}
      user={{id:100}}
    />);

    expect(wrapper.find('a[href="https://workbenchdata.com"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Undo"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Redo"]')).toHaveLength(0);
    expect(wrapper.find('span[children="Import Module"]')).toHaveLength(1);
    expect(wrapper.find('span[children="Log Out"]')).toHaveLength(1);
  })
});
