/**
 * Testing Stories:
 * -Renders icon
 * -Mouse events on icon will show/hide full card
 * -Icon and card can be dragged
 * -Click on button will find data-loading module and update notifications
 */

import React from 'react'
import AddNotificationButtonClosed  from './AddNotificationButtonClosed'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'
var reducer = require("./workflow-reducer");

describe('AddNotificationButtonClosed ', () => {

  var wrapper;  
  var mockSetOpenCategory;

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

      mockSetOpenCategory = jest.fn();

      wrapper = mount(
          <DragDropContextProvider backend={HTML5Backend}>
              <AddNotificationButtonClosed setOpenCategory={mockSetOpenCategory}/>
          </DragDropContextProvider>
      );
  });
  afterEach(() => wrapper.unmount());    

  it('Renders', () => { 
    expect(wrapper).toMatchSnapshot();
    // find matching icon
    expect(wrapper.find('.icon-notification')).toHaveLength(1);
  });

  it('Mouse events on icon will show/hide full card', () => { 
    let icon = wrapper.find('.notification-button-closed');
    let popout = wrapper.find('.notification-button-popout');
    // check that card not displayed initially (governed by 'display' property)
    expect(popout.props().style).toEqual({display:'none'});
    // simulate mouse enter
    icon.simulate('mouseEnter');
    expect(mockSetOpenCategory.mock.calls.length).toBe(1);
    // look for card display
    expect(popout.props().style).toEqual({display:'block'});
    // simulate mouse leave
    icon.simulate('mouseLeave');
    // check that card not displayed again
    expect(popout.props().style).toEqual({display:'none'});
  });

  it('Should fire click events on click', () => {
      let icon = wrapper.find('.notification-button-closed');
      icon.simulate('click');
      expect(reducer.store.getState.mock.calls.length).toBe(1);
      expect(reducer.store.dispatch.mock.calls.length).toBe(1);
      expect(reducer.updateWfModuleAction.mock.calls[0][0]).toBe(1); //Should have found wfmodule id 1
      expect(reducer.updateWfModuleAction.mock.calls[0][1].notifications).toBe(true);
  });

  it('Card is draggable', () => { 
    // search for property on the component that indicates drag-ability
    expect( Object.keys(wrapper.find('AddNotificationButtonClosed').props()).includes('connectDragSource') ).toBe(true);
  });
});
