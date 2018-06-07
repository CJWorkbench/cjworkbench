import React from 'react'
import GoogleConnect  from './GoogleConnect'
import { mount, ReactWrapper } from 'enzyme'
import { jsonResponseMock } from '../utils'
import { store,  getCurrentUserAction, disconnectCurrentUserAction } from '../workflow-reducer';
jest.mock('../workflow-reducer');

describe('GoogleConnect', () => {
  it('Mounts correctly without user creds', (done) => {
    const wrapper = mount(<GoogleConnect userCreds={null} />)
    expect(wrapper).toMatchSnapshot();
    const connectButton = wrapper.find('button.connect');
    expect(connectButton).toHaveLength(1);
    done();
  });

  it('Mounts correctly with user creds and fires call to delete creds on click', (done) => {
    const wrapper = mount(<GoogleConnect userCreds={0} />)
    expect(wrapper).toMatchSnapshot();
    const disconnectButton = wrapper.find('button.disconnect');
    expect(disconnectButton).toHaveLength(1);
    disconnectButton.simulate('click');
    expect(disconnectCurrentUserAction.mock.calls.length).toBe(1);
    done();
  });
});
