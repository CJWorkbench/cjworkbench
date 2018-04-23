import React from 'react'
import {store, setSelectedWfModuleAction} from "./workflow-reducer";
import {getPageID} from "./utils";
import WorkbenchAPI from './WorkbenchAPI'

var api = WorkBenchAPI();
export function mockAPI(mock_api) {
  api = mock_api;
}

export function updateSort(wfModuleId, sortInfo) {
    var state = store.getState();

    console.log(state);
}