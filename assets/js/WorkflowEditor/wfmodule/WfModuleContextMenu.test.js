import React from 'react'
import WfModuleContextMenu  from './WfModuleContextMenu'
import { mount } from 'enzyme'

describe('WfModuleContextMenu', () => {

  let wrapper;
  let removeModule;
  
  beforeEach(() => {
    removeModule = jest.fn();

    wrapper = mount(
      <WfModuleContextMenu
        removeModule={removeModule} 
        id={415}
        className="menu-test-class"        
      />
    )
  });

  afterEach(() => wrapper.unmount());

  it('should match snapshot', () => {
    expect(wrapper).toMatchSnapshot()
  });

  // only checking the call to removeModule(), not the removal
  it('Renders menu option to Delete with onClick method', () => { 
    // open the context menu
    wrapper.find('button.context-button').simulate('click')

    const deleteButton = wrapper.find('button.test-delete-button');
    expect(deleteButton).toHaveLength(1);
    deleteButton.simulate('click');
    expect(removeModule).toHaveBeenCalled()
  });

  it('should open and close the export modal', () => {
    let modal;

    // open the context menu
    wrapper.find('button.context-button').simulate('click')

    // open the modal window
    const exportButton = wrapper.find('button.test-export-button');
    exportButton.simulate('click');
    expect(wrapper.find('div.modal-dialog')).toHaveLength(1);

    // close it (via callback)
    wrapper.instance().toggleExportModal();
    wrapper.update();
    expect(wrapper.find('div.modal-dialog')).toHaveLength(0);
  });
});
