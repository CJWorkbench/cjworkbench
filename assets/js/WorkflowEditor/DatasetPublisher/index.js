import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import selectDataset from '../../selectors/selectDataset'
import selectLastPublishDatasetRequest from '../../selectors/selectLastPublishDatasetRequest'
import { beginPublishDataset } from './actions'
import Form from './Form'

export default function DatasetPublisher (props) {
  const dispatch = useDispatch()
  const handleClickPublish = React.useCallback(() => { dispatch(beginPublishDataset()) }, [dispatch])
  const dataset = useSelector(selectDataset)
  const lastPublishRequest = useSelector(selectLastPublishDatasetRequest)

  return (
    <div className='dataset-publisher'>
      {dataset ? <><h2>Dataset</h2><pre>{JSON.stringify(dataset, null, 2)}</pre></> : null}
      {lastPublishRequest ? <><h2>Last request</h2><pre>{JSON.stringify(lastPublishRequest, null, 2)}</pre></> : null}
      <Form />
      <button
        type='button'
        onClick={handleClickPublish}
      >
        TODO:i18n publish
      </button>
    </div>
  )
}
