import React from 'react'
import { DataVersionSelectTest as DataVersionSelect }  from './DataVersionSelect'
import { mapStateToProps }  from './DataVersionSelect'
import { mount, ReactWrapper } from 'enzyme'
import { okResponseMock, jsonResponseMock } from '../test-utils'
import * as workflowReducer from '../workflow-reducer'
import {findIdxByProp} from "../workflow-reducer";

jest.useFakeTimers();

// Guarantees for writing tests:
// - At least three modules
// - Module ids increment by 10
// - First module adds data and has data versions and unread notifications
export const genericTestWorkflow = {
  id: 999,
  selected_wf_module: 2,  // different than test_state.selected_wf_module so we can test setting state.selected_wf_module
  wf_modules: [
    {
      id: 10,
      parameter_vals: [
        {
          id: 1,
          parameter_spec : {
            id_name: 'data',
          },
          value: 'Some Data'
        }
      ],
      versions: {
        selected: "2018-02-21T03:09:20.214054Z",
        versions: [
          ["2018-02-21T03:09:20.214054Z", true],
          ["2018-02-21T03:09:15.214054Z", false],
          ["2018-02-21T03:09:10.214054Z", false]
        ]
      },
      has_unseen_notification: true,
    },
    {
      id: 20
    },
    {
      id: 30
    },
  ],
};

describe('DataVersionSelect', () => {

  var mockVersions = {
    versions: [
      ['2017-07-10 17:57:58.324Z', false],
      ['2017-06-10 17:57:58.324Z', true],
      ['2017-05-10 17:57:58.324Z', true],
      ['2017-04-10 17:57:58.324Z', true],
      ['2017-03-10 17:57:58.324Z', true]
    ],
    selected: '2017-04-10 17:57:58.324Z'
  };
  var api;
  var wrapper;

  beforeEach(() => {
    api = {
      // Called by DataVersionSelect
      setWfModuleVersion: okResponseMock(),

      // Called by reducer actions
      markDataVersionsRead: okResponseMock(),
      updateWfModule: okResponseMock(),
      loadWorkflow: (() => { return new Promise(()=>{}) })  // won't resolve, so never load new workflow during test
    };

    workflowReducer.mockAPI(api);

    // Mount is necessary to invoke componentDidMount()
    wrapper = mount(
      <DataVersionSelect
        isReadOnly={false}
        wfModuleId={808}
        revision={202}
        api={api}
        setClickNotification={()=>{return false}}
        testing={true}
        versions={mockVersions}
        notifications={true}
        markDataVersionsRead={jest.fn()}
        updateWfModuleAction={jest.fn()}
        setDataVersionAction={jest.fn()}
      />);
  });

  afterEach(() => {
    wrapper.unmount();
  });


  it('Renders correctly when in Private mode, and selection is confirmed when user hits OK', (done) => {

    expect(wrapper).toMatchSnapshot();  // 1

    // Start with dialog closed
    expect(wrapper.state().modalOpen).toBe(false);

    // give versions a chance to load
    setImmediate( () => {
      wrapper.update()
      var modalLink = wrapper.find('div.open-modal');
      expect(modalLink).toHaveLength(1);
      expect(wrapper.find('.action-link').text()).toEqual("2 of 5");

      modalLink.simulate('click');
      expect(wrapper.state().modalOpen).toBe(true);

      const modal = wrapper.find('div.modal-dialog');
      expect(modal).toMatchSnapshot(); // 2
      expect(modal.find('div.list-body')).toHaveLength(1);

      // check that the versions have loaded and are displayed in list
      const versionsList = modal.find('div.list-test-class');
      expect(versionsList).toHaveLength(5);

      // filter list to grab first item
      const firstVersion = versionsList.filterWhere(n => n.key() == '2017-07-10 17:57:58.324Z');
      firstVersion.simulate('click');

      expect(wrapper.state().dialogSelected).toEqual('2017-07-10 17:57:58.324Z');
      //expect(wrapper.state().originalSelected).toEqual('2017-04-10 17:57:58.324Z');

      const okButton = modal.find('.test-ok-button');
      okButton.first().simulate('click');

      // state needs to update and modal needs to close
      setImmediate( () => {
        expect(wrapper).toMatchSnapshot(); // 3
        expect(wrapper.state().modalOpen).toBe(false);
        expect(wrapper.props().setDataVersionAction.mock.calls.length).toBe(1);
        done();
      });
    });
  });

  // Pared-down version of first test
  it('Does not save selection when user hits Cancel', (done) => {

    setImmediate( () => {
      wrapper.update()
      var modalLink = wrapper.find('div.open-modal');
      expect(modalLink).toHaveLength(1);
      modalLink.simulate('click');
      expect(wrapper.state().modalOpen).toBe(true);

      const modal = wrapper.find('div.modal-dialog');

      // check that the versions have loaded and are displayed in list
      const versionsList = modal.find('div.list-test-class');
      expect(versionsList).toHaveLength(5);
      const lastVersion = versionsList.filterWhere(n => n.key() == '2017-03-10 17:57:58.324Z');
      lastVersion.simulate('click');

      expect(wrapper.state().dialogSelected).toEqual('2017-03-10 17:57:58.324Z');

      const cancelButton = modal.find('.test-cancel-button');
      cancelButton.first().simulate('click');

      // state needs to update and modal needs to close
      setImmediate( () => {
        expect(wrapper).toMatchSnapshot();              // 4
        expect(wrapper.state().modalOpen).toBe(false);
        expect(wrapper.state().dialogSelected).toEqual('2017-04-10 17:57:58.324Z');
        expect(wrapper.props().setDataVersionAction.mock.calls.length).toBe(0); // never called because user cancelled
        done();
      });
    });
  });

  it('Does not open modal when in read-only mode', (done) => {
    let readOnlywrapper = mount(<DataVersionSelect
      isReadOnly={true}
      wfModuleId={808}
      revision={202}
      api={api}
      testing={true}
      setClickNotification={()=>{return false;}}
      versions={mockVersions}
      notifications={true}
      markDataVersionsRead={jest.fn()}
      updateWfModuleAction={jest.fn()}
      setDataVersionAction={jest.fn()}
    />);

    setImmediate(() => {
      let readOnlyModalLink = readOnlywrapper.find('div.open-modal');

      readOnlyModalLink.simulate('click');
      expect(readOnlywrapper.state().modalOpen).toBe(false);

      done();
    });
  });

  it('Displays empty when no versions available', (done) => {

    var emptyApi = {
      getWfModuleVersions: jsonResponseMock({versions: [], selected: null}),
      setWfModuleVersion: okResponseMock(),
    };

    let wrapper2 = mount(<DataVersionSelect
      isReadOnly={true}
      wfModuleId={808}
      revision={202}
      api={emptyApi}
      testing={true}
      setClickNotification={()=>{return false;}}
      versions={{versions: [], selected: null}}
      notifications={true}
      markDataVersionsRead={jest.fn()}
      updateWfModuleAction={jest.fn()}
      setDataVersionAction={jest.fn()}
    />);

    setImmediate( () => {
      var modalLink2 = wrapper2.find('div.open-modal');
      expect(modalLink2).toHaveLength(1);
      expect(modalLink2.text()).toBe('-');

      expect(wrapper2).toMatchSnapshot();
      done();
    });

  });

  it('mapStateToProps works correctly', () =>{
    let mockState = {
      workflow: genericTestWorkflow
    };
    let mockProps = {
      wfModuleId : 10  // module which has unread notifications
    }

    let { notifications, versions } = mapStateToProps(mockState, mockProps);

    expect(notifications).toBe(mockState.workflow.wf_modules[0].notifications);
    expect(versions).toBe(mockState.workflow.wf_modules[0].versions);
  })
});
