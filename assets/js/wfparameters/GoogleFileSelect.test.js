import React from 'react'
import GoogleFileSelect  from './GoogleFileSelect'
import { mount, shallow } from 'enzyme'
import { jsonResponseMock } from '../test-utils'

describe('FileSelect', () => {
  let gDriveFileMeta = JSON.stringify({
    "kind": "drive#file",
    "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
    "name": "Police Data",
    "mimeType": "application/vnd.google-apps.spreadsheet"
  })

  const gDriveFiles = {
    "kind": "drive#fileList",
    "incompleteSearch": false,
    "files": [
      {
        "kind": "drive#file",
        "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
        "name": "Police Data",
        "mimeType": "application/vnd.google-apps.spreadsheet"
      },
      {
        "kind": "drive#file",
        "id": "jdsiu9cu89BJHBI789fdsfdsLAHY5637hdnbthywhsua",
        "name": "Government Contracts",
        "mimeType": "application/vnd.google-apps.spreadsheet"
      },
      {
        "kind": "drive#file",
        "id": "sdf987IBHJB98uc9uisdjaushwyhtbndh7365YHALsdf",
        "name": "Labor and materials",
        "mimeType": "application/vnd.google-apps.spreadsheet"
      },
      {
        "kind": "drive#file",
        "id": "fdsLAHY5637hdnbthywhsuajdsiu9cu89BJHBI789fds",
        "name": "Budget",
        "mimeType": "application/vnd.google-apps.spreadsheet"
      },
      {
        "kind": "drive#file",
        "id": "9BJHBI789fdsfdsLAHY5637hdnbthywhsuajdsiu9cu8",
        "name": "Science Data",
        "mimeType": "application/vnd.google-apps.spreadsheet"
      }
    ]
  };

  // Mount is necessary to invoke componentDidMount()
  let api;
  beforeEach(() => {
    api = {
      postParamEvent: jsonResponseMock(gDriveFiles)
    }
  })

  it('Loads correctly and allows a user to choose a new file', (done) => {
    const wrapper = mount(
      <GoogleFileSelect
        api={api}
        userCreds={[0]}
        pid={1}
        saveState={ (state) => { gDriveFileMeta = JSON.stringify(state); } }
        getState={() => { return gDriveFileMeta; }}
      />
    );

    expect(api.postParamEvent.mock.calls.length).toBe(1);

    expect(wrapper).toMatchSnapshot();

    // should call API for its data on componentDidMount
    expect(wrapper.state().modalOpen).toBe(false);

    setImmediate( () => {
      wrapper.update();
      const fileName = wrapper.find('span.t-d-gray.content-3.mb-3');
      const modalLink = wrapper.find('.file-info .t-f-blue');
      expect(fileName.text()).toEqual('Police Data');
      modalLink.simulate('click');

      setImmediate( () => {
        wrapper.update();
        expect(wrapper.state().modalOpen).toBe(true);

        const modal = wrapper.find('div.modal-dialog');
        expect(modal).toMatchSnapshot();
        expect(modal.find('div.list-body')).toHaveLength(1);

        expect(wrapper.state().files).toEqual(gDriveFiles['files']);
        const filesListItems = modal.find('.line-item--data-version');
        expect(filesListItems).toHaveLength(5);

        const secondListItem = filesListItems.filterWhere(n => n.key() == 1);
        secondListItem.simulate('click');

        setImmediate( () => {
          expect(wrapper.state().file).toEqual({
            "kind": "drive#file",
            "id": "jdsiu9cu89BJHBI789fdsfdsLAHY5637hdnbthywhsua",
            "name": "Government Contracts",
            "mimeType": "application/vnd.google-apps.spreadsheet"
          });
          done();
        })

      });
    });
  });

  it('Shows the file count and larger button if there is no file and a user credential is present', (done) => {
    const noFileWrapper = shallow(
      <GoogleFileSelect
        api={api}
        userCreds={[0]}
        pid={1}
        saveState={ (state) => { gDriveFileMeta = JSON.stringify(state); } }
        getState={() => ''}
      />
    )

    expect(api.postParamEvent).toHaveBeenCalled()

    setImmediate(() => {
      noFileWrapper.update()
      const fileCount = noFileWrapper.find('.file-info p')
      expect(fileCount).toHaveLength(1)
      expect(fileCount.text()).toBe('5 files found')

      const modalLink = noFileWrapper.find('.button-orange.action-button')
      expect(modalLink).toHaveLength(1)

      done()
    })
  })

  it('Does not show the modal link if there is no user credential present', () => {
    const noCredsWrapper = shallow(
      <GoogleFileSelect
        api={api}
        userCreds={[]}
        pid={1}
        saveState={ (state) => { gDriveFileMeta = JSON.stringify(state); } }
        getState={() => { return gDriveFileMeta; }}
      />
    )

    expect(api.postParamEvent).not.toHaveBeenCalled()
    expect(noCredsWrapper).toMatchSnapshot();

    const modalLink = noCredsWrapper.find('.file-info .t-f-blue')

    expect(modalLink).toHaveLength(0)
  })

  it('Does not show anything if neither a user credential nor a file are present', (done) => {
    var noCredsNoFileWrapper = shallow(
      <GoogleFileSelect
        api={api}
        userCreds={[]}
        pid={1}
        saveState={ (state) => { gDriveFileMeta = JSON.stringify(state); } }
        getState={() => { return ''; }}
      />
    )

    expect(api.postParamEvent).not.toHaveBeenCalled()
    expect(noCredsNoFileWrapper).toMatchSnapshot();

    expect(noCredsNoFileWrapper.find('gdrive-fileSelect').length).toBe(0);

    done();
  });

});
