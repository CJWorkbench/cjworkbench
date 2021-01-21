import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

const AnimationTimeInMs = 10 // see _ShareUrl.scss

export default function ShareUrl (props) {
  const inputRef = React.useRef()
  const { download = false, go = false, url } = props
  const [lastUsedDate, setLastUsedDate] = React.useState(null)

  const handleClickCopy = React.useCallback(() => {
    if (inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
    window.navigator.clipboard.writeText(url).then(() => { setLastUsedDate(new Date()) })
  }, [inputRef, url, setLastUsedDate])

  const handleClickDownload = React.useCallback(() => {
    // Don't ev.preventDefault()! We'll continue with the download; we just
    // want to animate as well.
    setLastUsedDate(new Date())
  }, [setLastUsedDate])

  const handleClickGo = handleClickDownload

  React.useLayoutEffect(
    () => {
      if (lastUsedDate !== null) {
        const timeout = window.setTimeout(() => setLastUsedDate(null), AnimationTimeInMs)
        return () => window.clearTimeout(timeout)
      }
    },
    [lastUsedDate, setLastUsedDate]
  )

  // Show as an <input> so that the user can press Ctrl+A to select all the text
  return (
    <div className='share-url'>
      <div className={`url-container${lastUsedDate === null ? '' : ' used'}`}>
        <input readOnly name='url' ref={inputRef} value={url} />
      </div>
      <button name='copy' onClick={handleClickCopy}>
        <Trans id='js.components.ShareUrl.copy'>Copy</Trans>
      </button>
      {download ? (
        <a href={url} download onClick={handleClickDownload}>
          <Trans id='js.components.ShareUrl.download'>Download</Trans>
        </a>
      ) : null}
      {go ? (
        <a href={url} target='_blank' rel='noopener noreferrer' onClick={handleClickGo}>
          <Trans id='js.components.ShareUrl.go'>Go</Trans>
        </a>
      ) : null}
    </div>
  )
}
ShareUrl.propTypes = {
  url: PropTypes.string.isRequired,
  download: PropTypes.bool,
  go: PropTypes.bool
}
