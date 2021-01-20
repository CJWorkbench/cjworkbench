import React from 'react'
import PropTypes from 'prop-types'
import { timeDifference } from './utils'
import { i18n } from '@lingui/core'
import { Trans } from '@lingui/macro'
import EmbedIcon from '../icons/embed.svg'

function IframeContainer (props) {
  const { step } = props
  return (
    <div className='iframe-container'>
      <iframe src={'/api/wfmodules/' + step.id + '/output'} />
    </div>
  )
}

function Logo (props) {
  return (
    <a className='logo' href='https://workbenchdata.com' target='_blank' rel='noopener noreferrer'>
      <img src={`${window.STATIC_URL}images/logo.png`} width='35' alt='Workbench' />
    </a>
  )
}

function EmbedButton (props) {
  const { step } = props
  const [isOpen, setOpen] = React.useState(false)

  const iframeCode = `<iframe src="${window.location.origin}/embed/${step.id} width="560" height="315" frameborder="0"></iframe>`
  const handleClickOpen = React.useCallback(() => setOpen(true), [setOpen])
  const handleClickClose = React.useCallback(() => setOpen(false), [setOpen])

  return (
    <>
      <button name='embed' type='button' onClick={handleClickOpen}>
        <EmbedIcon />
      </button>
      <div className={'embed-overlay' + (isOpen ? ' open' : '')} onClick={handleClickClose}>
        <div className='embed-share-links' onClick={(e) => { e.stopPropagation() }}>
          <h1><Trans id='js.Embed.embedThisChart' comment='This should be all-caps for styling reasons'>EMBED THIS CHART</Trans></h1>
          <h2><Trans id='js.Embed.embedCode'>Paste this code into any webpage HTML</Trans></h2>
          <div className='code-snippet'>
            <code className='embed--share-code'>
              {iframeCode}
            </code>
          </div>
        </div>
      </div>
    </>
  )
}

function Footer (props) {
  const { workflow, step } = props
  const timeAgo = timeDifference(workflow.last_update, new Date(), i18n)

  return (
    <footer>
      <Logo />
      <div className='metadata'>
        <h1>
          <a href={`/workflows/${workflow.id}/`} target='_blank' rel='noopener noreferrer'>
            {workflow.name}
          </a>
        </h1>
        <ul>
          <li><Trans id='js.Embed.metadata.author'>by {workflow.owner_name}</Trans></li>
          <li>
            <Trans
              id='js.Embed.metadata.updated'
              comment="`<0>{timeAgo}</0>` will show a time difference (i.e. something like '4h ago')"
            >
              Updated <time time={workflow.last_update}>{timeAgo}</time>
            </Trans>
          </li>
        </ul>
      </div>
      <EmbedButton step={step} />
    </footer>
  )
}

function NotAvailable () {
  return (
    <>
      <p className='not-available'><Trans id='js.Embed.workflowNotAvailable.title'>This workflow is not available</Trans></p>
      <footer>
        <Logo />
        <div className='embed-footer-meta'>
          <h1><Trans id='js.Embed.workflowNotAvailable.footer.logo'>Workbench</Trans></h1>
        </div>
      </footer>
    </>
  )
}

export default function Embed (props) {
  const { workflow, step } = props

  if (!workflow && !step) {
    return <NotAvailable />
  }

  return (
    <>
      <IframeContainer step={step} />
      <Footer workflow={workflow} step={step} />
    </>
  )
}
Embed.propTypes = {
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    last_update: PropTypes.string.isRequired, // ISO8601 String
    owner_name: PropTypes.string.isRequired
  }), // or null, on error
  step: PropTypes.shape({
    id: PropTypes.number.isRequired // TODO migrate to workflowId+stepSlug URLs
  }) // or null, on error
}
