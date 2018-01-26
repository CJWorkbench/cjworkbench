/**
 * Testing Stories:
 * -Renders card
 * -Card can be dragged 
 * 
 */

import React from 'react'
import AddNotificationButtonOpen  from './AddNotificationButtonOpen'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'
var reducer = require('./workflow-reducer.js');


describe('AddNotificationButtonOpen ', () => {

  var wrapper;

  beforeEach(() => {
    var mockGetState = jest.fn();
    mockGetState.mockReturnValue({
       workflow: {
           wf_modules: [
               {
                   id: 1,
                   notifications: false,
                   module_version: {
                       module: {
                           loads_data: true
                       }
                   }
               },
               {
                   id: 2,
                   notifications: false,
                   module_version: {
                       module: {
                           loads_data: false
                       }
                   }
               }
           ]
       }
    });

    reducer.store = {
        getState: mockGetState,
        dispatch: jest.fn()
    };

    reducer.updateWfModuleAction = jest.fn();

    wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <AddNotificationButtonOpen/>
      </DragDropContextProvider>
    );
  });
  afterEach(() => wrapper.unmount());    

  it('Renders', () => { 
    expect(wrapper).toMatchSnapshot();
    // find matching icon
    expect(wrapper.find('.icon-notification')).toHaveLength(1);
  });

  it('Finds correct wfmodule on click and dispatches change to notifications', () => {
    var button = wrapper.find('.icon-notification');
    button.simulate('click');
    expect(reducer.store.getState.mock.calls.length).toBe(1);
    expect(reducer.updateWfModuleAction.mock.calls[0][0]).toBe(1);
    expect(reducer.updateWfModuleAction.mock.calls[0][1].notifications).toBe(true);
  });

  it('Card is draggable', () => {
    // search for property on the component that indicates drag-ability
    expect( Object.keys(wrapper.find('AddNotificationButtonOpen').props()).includes('connectDragSource') ).toBe(true);
  });

});
