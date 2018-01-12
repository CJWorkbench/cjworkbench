import React from 'react'
import GoogleConnect  from './GoogleConnect'
import { mount, ReactWrapper } from 'enzyme'
import { jsonResponseMock } from '../utils'
import { store,  updateCurrentUserAction, disconnectCurrentUserAction } from '../workflow-reducer';
jest.mock('../workflow-reducer');

describe('GoogleConnect', () => {
  it('Mounts correctly without user creds', (done) => {
    var wrapper = mount(<GoogleConnect
      userCreds={[]}
    />)
    expect(wrapper).toMatchSnapshot();
    var connectButton = wrapper.find('.action-button.button-orange.centered');
    expect(connectButton).toHaveLength(1);
    done();
  });

  it('Mounts correctly with user creds and fires call to delete creds on click', (done) => {
    var wrapper = mount(<GoogleConnect
      userCreds={[0]}
    />)
    expect(wrapper).toMatchSnapshot();
    var disconnectButton = wrapper.find('.t-f-blue');
    expect(disconnectButton).toHaveLength(1);
    disconnectButton.simulate('click');
    expect(disconnectCurrentUserAction.mock.calls.length).toBe(1);
    done();
  });
});
