/**
 * Testing Stories:
 * -Renders icon
 * -Mouse events on icon will show/hide full card
 * -Icon and card can be dragged
 * -Click on button will find data-loading module and update notifications
 *
 */

import React from 'react'
import AddNotificationButtonClosed  from './AddNotificationButtonClosed'
import AddNotificationButtonOpen  from './AddNotificationButtonOpen'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'
const reducer = require("./workflow-reducer");

const notificationsOffFactory = function() {
    return jest.fn().mockReturnValue({
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
};

const notificationsOnFactory = function() {
    return jest.fn().mockReturnValue({
         workflow: {
             wf_modules: [
                 {
                     id: 1,
                     notifications: true,
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
};


const notificationToggleTest = function(el, reducer) {
    el.simulate('click');
    expect(reducer.store.getState.mock.calls.length).toBe(1);
    expect(reducer.updateWfModuleAction.mock.calls[0][0]).toBe(1);
    expect(reducer.updateWfModuleAction.mock.calls[0][1].notifications).toBe(true);

    reducer.store.getState = notificationsOnFactory(); // Set notifications to "on" to test that we do't make the API call a second time

    el.simulate('click');
    expect(reducer.updateWfModuleAction.mock.calls.length).toBe(1);
};

describe('AddNotificationButtonClosed', () => {

  let wrapper;

  beforeEach(() => {
      reducer.store = {
          getState: notificationsOffFactory(),
          dispatch: jest.fn()
      };
      reducer.updateWfModuleAction = jest.fn();

      wrapper = mount(
          <DragDropContextProvider backend={HTML5Backend}>
              <AddNotificationButtonClosed/>
          </DragDropContextProvider>
      );
  });
  afterEach(() => wrapper.unmount())

  it('matches snapshot', () => {
    expect(wrapper).toMatchSnapshot()
  })

  it('has a notification icon', () => {
    expect(wrapper.find('.icon-notification')).toHaveLength(1)
  })

  it('Mouse events on icon will show/hide full card', () => {
    const icon = wrapper.find('.notification-button-closed');
    // check that card not displayed initially (Bootstrap d-none class)
    expect(wrapper.find('.card.d-none')).toHaveLength(1)
    // simulate mouse enter
    icon.simulate('mouseEnter')
    // look for card display
    expect(wrapper.find('.card.d-none')).toHaveLength(0)
    // simulate mouse leave
    icon.simulate('mouseLeave');
    // check that card not displayed again
    expect(wrapper.find('.card.d-none')).toHaveLength(1)
  });

  it('Finds correct wfmodule on click and dispatches change to notifications', () => {
      const icon = wrapper.find('.notification-button-closed');
      notificationToggleTest(icon, reducer);
  });

  it('Card is draggable', () => {
    // search for property on the component that indicates drag-ability
    expect( Object.keys(wrapper.find('AddNotificationButtonClosed').props()).includes('connectDragSource') ).toBe(true);
  });
});

describe('AddNotificationButtonOpen', () => {

  let wrapper;

  beforeEach(() => {
    reducer.store = {
        getState: notificationsOffFactory(),
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

  it('matches snapshot', () => {
    expect(wrapper).toMatchSnapshot()
  })

  it('has a notification icon', () => {
    expect(wrapper.find('.icon-notification')).toHaveLength(1)
  })

  it('Finds correct wfmodule on click and dispatches change to notifications', () => {
    const button = wrapper.find('.icon-notification');
    notificationToggleTest(button, reducer);
  });

  it('Card is draggable', () => {
    // search for property on the component that indicates drag-ability
    expect( Object.keys(wrapper.find('AddNotificationButtonOpen').props()).includes('connectDragSource') ).toBe(true);
  });

});
