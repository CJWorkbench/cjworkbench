import React from 'react'
import PropTypes from 'prop-types'
import propTypes from './propTypes'
import { connect } from 'react-redux'
import { Trans, t } from '@lingui/macro'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './components/Modal'
import { setStepParamsAction } from './workflow-reducer'
import { setWorkflowPublicAccessAction } from './ShareModal/actions'
import { useChartIframeSrcWithDataUrlSubscription } from './ChartIframe'
import EmbedIcon from '../icons/embed.svg'

function IframeWithEmbedButton (props) {
  const { iframeRef, isPublic, src, embedUrl, onClickSetWorkflowPublic } = props
  const [isModalOpen, setModalOpen] = React.useState(false)

  const handleClickOpenModal = React.useCallback(() => setModalOpen(true), [setModalOpen])
  const handleClickCloseModal = React.useCallback(() => setModalOpen(false), [setModalOpen])

  return (
    <>
      <iframe src={src} ref={iframeRef} />
      <button
        name='embed'
        title={t({
          id: 'js.OutputIframe.getEmbeddableUrl.hoverText',
          message: 'Get an embeddable URL'
        })}
        onClick={handleClickOpenModal}
      >
        <EmbedIcon />
      </button>
      {(isModalOpen && !isPublic)
        ? (
          <PublicModal
            onClose={handleClickCloseModal}
            onClickSetWorkflowPublic={onClickSetWorkflowPublic}
          />
          )
        : null}
      {(isModalOpen && isPublic)
        ? (
          <EmbedModal
            onClose={handleClickCloseModal}
            embedUrl={embedUrl}
          />
          )
        : null}
    </>
  )
}
IframeWithEmbedButton.propTypes = {
  src: PropTypes.string.isRequired,
  iframeRef: PropTypes.func.isRequired, // func(el) => undefined
  embedUrl: PropTypes.string.isRequired,
  isPublic: PropTypes.bool.isRequired,
  onClickSetWorkflowPublic: PropTypes.func.isRequired // func() => undefined
}

/**
 * An iframe with maybe-constant `src` set to `${moduleUrl}?dataUrl=${dataUrl}`
 *
 * If the iframe sends `postMessage({ type: 'subscribe-to-data-url' })`, then we
 * "lock" the `src` and send new `dataUrl` via `postMessage()` instead.
 */
function StickyResultJsonIframeWithEmbedButton (props) {
  const { workflowIdOrSecretId, moduleSlug, stepSlug, deltaId, onResize, onSetStepParams, isPublic, embedUrl, onClickSetWorkflowPublic } = props
  const [iframeEl, setIframeEl] = React.useState(null)

  const src = useChartIframeSrcWithDataUrlSubscription({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId, iframeEl })

  const handleMessage = React.useCallback(ev => {
    if (!iframeEl || ev.source !== iframeEl.contentWindow) {
      return
    }

    if (ev.origin !== new URL(src).origin) {
      return
    }

    const data = ev.data
    switch (data.type) {
      case 'resize':
        onResize({ height: data.height })
        break
      case 'set-params':
        onSetStepParams(data.params)
        break
    }
  }, [iframeEl, onResize, onSetStepParams, src])

  // On first render, clear the height. It may have been set by a previous
  // <StickyResultJsonIframeWithEmbedButton> in this same position.
  React.useEffect(() => {
    onResize({ height: src === null ? 0 : null })
  }, [onResize])

  // Install message handler, to handle messages from iframe.
  // When we change src, the old handler is removed and a new one is added.
  React.useEffect(() => {
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [handleMessage])

  if (src === null) {
    return null
  }

  return (
    <IframeWithEmbedButton
      key={src}
      src={src}
      iframeRef={setIframeEl}
      isPublic={isPublic}
      embedUrl={embedUrl}
      onClickSetWorkflowPublic={onClickSetWorkflowPublic}
    />
  )
}

/**
 * An iframe for the given step.
 *
 * This uses `key` to make sure that the inner `StickyResultJsonIframeWithEmbedButton`
 * "resets" every time we navigate to a new module. (Without this `key`,
 * a "locked" iframe wouldn't navigate to a new HTML page even when we
 * navigate from a "Python Code" step to a "Column Chart" step.
 */
function StepResultJsonIframeWithEmbedButton (props) {
  const { workflowIdOrSecretId, stepId, stepSlug, deltaId, isPublic, moduleSlug, onResize, onSetStepParams, onClickSetWorkflowPublic } = props
  const handleSetStepParams = React.useCallback(params => {
    onSetStepParams(stepId, params)
  }, [stepId, onSetStepParams])

  return (
    <StickyResultJsonIframeWithEmbedButton
      key={moduleSlug}
      moduleSlug={moduleSlug}
      workflowIdOrSecretId={workflowIdOrSecretId}
      stepSlug={stepSlug}
      deltaId={deltaId}
      embedUrl={`${window.origin}/workflows/${workflowIdOrSecretId}/steps/${stepSlug}/embed`}
      isPublic={isPublic}
      onResize={onResize}
      onSetStepParams={handleSetStepParams}
      onClickSetWorkflowPublic={onClickSetWorkflowPublic}
    />
  )
}
StepResultJsonIframeWithEmbedButton.propTypes = {
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  moduleSlug: PropTypes.string, // null for "don't render iframe"
  stepSlug: PropTypes.string, // null if no step
  stepId: PropTypes.number, // null if no step
  deltaId: PropTypes.number, // null if added to empty workflow
  onResize: PropTypes.func.isRequired, // func({height}) => undefined
  onClickSetWorkflowPublic: PropTypes.func.isRequired, // func() => undefined
  onSetStepParams: PropTypes.func.isRequired // func(stepId, params) => undefined
}

function PublicModal (props) {
  const { onClose, onClickSetWorkflowPublic } = props
  return (
    <Modal isOpen toggle={onClose}>
      <ModalHeader>
        <div className='modal-title'>
          <Trans
            id='js.OutputIframe.private.header.title'
            comment='This should be all-caps for styling reasons'
          >
            SHARE THIS WORKFLOW
          </Trans>
        </div>
      </ModalHeader>
      <ModalBody>
        <div className='title-3 mb-3'>
          <Trans id='js.OutputIframe.private.workflowIsPrivate'>
            This workflow is currently private
          </Trans>
        </div>
        <div className='info-3 t-d-gray'>
          <Trans id='js.OutputIframe.private.setToPublic'>
            Set this workflow to Public in order to share it? Anyone with the
            URL will be able to access and duplicate it.
          </Trans>
        </div>
      </ModalBody>
      <ModalFooter>
        <button
          type='button'
          onClick={onClose}
          className='button-gray action-button'
        >
          <Trans id='js.OutputIframe.footer.cancelButton'>Cancel</Trans>
        </button>
        <button
          type='button'
          onClick={onClickSetWorkflowPublic}
          className='button-blue action-button'
        >
          <Trans id='js.OutputIframe.footer.setPublicButton'>
            Set public
          </Trans>
        </button>
      </ModalFooter>
    </Modal>
  )
}
PublicModal.propTypes = {
  onClose: PropTypes.func.isRequired, // func() => undefined
  onClickSetWorkflowPublic: PropTypes.func.isRequired // func() => undefined
}

function EmbedModal (props) {
  const { onClose, embedUrl } = props

  return (
    <Modal isOpen toggle={onClose}>
      <ModalHeader>
        <div className='modal-title'>
          <Trans
            id='js.OutputIframe.embed.header.title'
            comment='This should be all-caps for styling reasons'
          >
            EMBED THIS CHART
          </Trans>
        </div>
      </ModalHeader>
      <ModalBody>
        <p className='info'>
          <Trans id='js.OutputIframe.embed.embedCode'>
            Paste this code into any webpage HTML
          </Trans>
        </p>
        <div className='code-snippet'>
          <code className='chart-embed'>&lt;iframe src="{embedUrl}" width="560" height="315" frameborder="0"&gt;&lt;/iframe&gt;</code>
        </div>
      </ModalBody>
      <div className='modal-footer'>
        <div
          onClick={onClose}
          className='button-gray action-button'
        >
          <Trans id='js.OutputIframe.footer.OKButton'>OK</Trans>
        </div>
      </div>
    </Modal>
  )
}
EmbedModal.propTypes = {
  embedUrl: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired // func() => undefined
}

export function OutputIframe (props) {
  const { isPublic, workflowIdOrSecretId, moduleSlug, stepSlug, stepId, deltaId, setStepParams, setWorkflowPublic } = props
  const [heightFromIframe, setHeightFromIframe] = React.useState(null)

  const handleResize = React.useCallback(size => {
    const height = size === null ? null : size.height
    setHeightFromIframe(height)
  }, [setHeightFromIframe])

  const style = React.useMemo(
    () => heightFromIframe === null ? null : { height: Math.ceil(heightFromIframe) },
    [heightFromIframe]
  )

  const classNames = ['outputpane-iframe']
  if (heightFromIframe !== null) {
    classNames.push('has-height-from-iframe')
    if (heightFromIframe === 0) {
      classNames.push('height-0')
    }
  }

  return (
    <div className={classNames.join(' ')} style={style}>
      <StepResultJsonIframeWithEmbedButton
        workflowIdOrSecretId={workflowIdOrSecretId}
        moduleSlug={moduleSlug}
        stepSlug={stepSlug}
        stepId={stepId}
        deltaId={deltaId}
        isPublic={isPublic}
        onClickSetWorkflowPublic={setWorkflowPublic}
        onSetStepParams={setStepParams}
        onResize={handleResize}
      />
    </div>
  )
}
OutputIframe.propTypes = {
  deltaId: PropTypes.number, // null if added to empty workflow
  stepId: PropTypes.number, // null if no step
  stepSlug: PropTypes.string, // null if no step
  moduleSlug: PropTypes.string, // null to disable iframe, even if there's a step
  isPublic: PropTypes.bool.isRequired,
  workflowIdOrSecretId: propTypes.workflowId.isRequired
}

const mapDispatchToProps = dispatch => {
  return {
    setWorkflowPublic: () => {
      dispatch((dispatch, getState, api) => {
        return dispatch(setWorkflowPublicAccessAction(true, Boolean(getState().workflow.secret_id)))
      })
    },
    setStepParams: (stepId, params) => {
      dispatch(setStepParamsAction(stepId, params))
    }
  }
}

export default connect(null, mapDispatchToProps)(OutputIframe)
