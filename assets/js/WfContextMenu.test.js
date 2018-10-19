import React from 'react'
import WfContextMenu  from './WfContextMenu'
import { shallow } from 'enzyme'

describe('WfContextMenu', () => {

  var api, wrapper;

  beforeEach( () => {
    api = {
      deleteWorkflow: jest.fn(),
      duplicateWorkflow: jest.fn()
    };

    wrapper = shallow(
      <WfContextMenu
        deleteWorkflow={api.deleteWorkflow}
        duplicateWorkflow={api.duplicateWorkflow}
        canDelete={true}
      />
    );
  });

  it('renders correctly', () => {
    expect(wrapper).toMatchSnapshot();
  });

  it('deletes workflow', () => {
    let deleteLink = wrapper.find('.test-delete-button');
    deleteLink.simulate('click');

    expect(api.deleteWorkflow.mock.calls.length).toBe(1);
  });

  it('duplicates workflow', () => {
    let dupLink = wrapper.find('.test-duplicate-button');
    dupLink.simulate('click');

    expect(api.duplicateWorkflow.mock.calls.length).toBe(1);
  });

  it('should not render a delete button', () => {
    const w = shallow(
      <WfContextMenu
        deleteWorkflow={api.deleteWorkflow}
        duplicateWorkflow={api.duplicateWorkflow}
        canDelete={false}
      />
    )

    expect(w.find('.test-delete-button')).toHaveLength(0)
  })

});
