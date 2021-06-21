import React from 'react'
import PropTypes from 'prop-types'
import { useDispatch, useSelector } from 'react-redux'
import propTypes from '../../../propTypes'
import { useWorkbenchAPI } from '../../../WorkbenchAPI'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../../components/Modal'
import Saving from '../../../components/Saving'
import { Trans, t } from '@lingui/macro'
import selectLoggedInUser from '../../../selectors/selectLoggedInUser'
import selectLoggedInUserIsPaying from '../../../selectors/selectLoggedInUserIsPaying'

const Day = 86400
const Hour = 3600
const Minute = 60

const StandardIntervals = [ Day, Hour, 10 * Minute ]

const PricePoint = PropTypes.oneOf(['ok', 'need-upgrade', 'over-limit'])

function AutofetchToggle (props) {
  const { checked, onChange, pricePoint } = props

  return (
    <div className='autofetch-toggle'>
      <label>
        <input
          type='checkbox'
          name='autofetch'
          disabled={pricePoint !== 'ok'}
          checked={checked}
          onChange={onChange}
        />
        {checked
          ? <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.AutofetchToggle.on'>ON</Trans>
          : <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.AutofetchToggle.off'>OFF</Trans>}
      </label>
      {pricePoint === 'need-upgrade'
        ? (
          <div className='need-upgrade'>
            <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.upgradeLink'>
              <a href="/settings/plan" target="_blank">Upgrade</a> to increase your limit
            </Trans>
          </div>)
        : null}
      {pricePoint === 'over-limit'
        ? (
          <div className='over-limit'>
            <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.overLimit'>
              Reduce usage elsewhere to allow updates here
            </Trans>
          </div>
        )
        : null}
    </div>
  )
}
AutofetchToggle.propTypes = {
  checked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired, // func(ev) => undefined
  pricePoint: PricePoint.isRequired
}

function describeInterval (nSeconds) {
  if (nSeconds % Day === 0) {
    return t({
      id: 'js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.nDays',
      message: '{n,plural,one {day} other {{n,number} days}}',
      values: { n: nSeconds / Day }
    })
  }
  if (nSeconds % Hour === 0) {
    return t({
      id: 'js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.nHours',
      message: '{n,plural,one {hour} other {{n,number} hours}}',
      values: { n: nSeconds / Hour }
    })
  }
  return t({
    id: 'js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.nMinutes',
    message: '{n,plural,one {minute} other {{n,number} minutes}}',
    values: { n: nSeconds / Minute }
  })
}

function IntervalOption (props) {
  const { value, pricePoint } = props

  return (
    <option value={value} disabled={pricePoint != 'ok'}>
      {describeInterval(value)}
      {pricePoint === 'need-upgrade'
        ? ` — ${t({ id: 'js.params.Custom.VersionSelect.UpdateFrequencySelectModal.upgrade', message: 'upgrade' })}`
        : null}
      {pricePoint === 'over-limit'
        ? ` — ${t({ id: 'js.params.Custom.VersionSelect.UpdateFrequencySelectModal.overLimit', message: 'over limit' })}`
        : null}
    </option>
  )
}
IntervalOption.propTypes = {
  value: PropTypes.number.isRequired, // seconds between updates
  pricePoint: PricePoint.isRequired
}

function countFetchesPerDay (isAutofetch, interval) {
  return isAutofetch ? 86400 / interval : 0
}

function handleSubmit (ev) {
  ev.stopPropagation()
  ev.preventDefault()
}

export default function UpdateFrequencySelectModal (props) {
  const {
    workflowId,
    stepSlug,
    isAutofetch,
    fetchInterval,
    isEmailUpdates,
    delayMsAfterServerOk = 500,
    onClose,
    setEmailUpdates
  } = props

  const dispatch = useDispatch()
  const api = useWorkbenchAPI()

  // { data: {isAutofetch, fetchInterval}, staleData: { fetchesPerDay, usage }, failed: bool?}
  const [submitting, setSubmitting] = React.useState(null)

  const currentFetchInterval = submitting ? submitting.data.fetchInterval : fetchInterval
  const currentIsAutofetch = submitting ? submitting.data.isAutofetch : isAutofetch

  const loggedInUser = useSelector(selectLoggedInUser)
  const loggedInUserIsPaying = useSelector(selectLoggedInUserIsPaying)

  // Our submits are asynchronous: 1) submit a change; 2) wait for the server to
  // catch up; 3) clear "submitting". During step 2, we _assume_ the usage based
  // on the _original_ usage plus the submitted number of fetches/day.
  const lastKnownUsage = submitting
    ? submitting.staleData.usage
    : loggedInUser.usage
  const lastKnownFetchesPerDayOnThisStep = submitting
    ? submitting.staleData.fetchesPerDay
    : countFetchesPerDay(isAutofetch, fetchInterval)
  const lastKnownFetchesElsewhere = lastKnownUsage.fetchesPerDay - lastKnownFetchesPerDayOnThisStep

  const findPricePoint = React.useCallback(
    fetchesPerDay => {
      if (currentIsAutofetch && fetchesPerDay <= 86400 / currentFetchInterval) {
        return 'ok'
      }
      if (fetchesPerDay + lastKnownFetchesElsewhere > loggedInUser.limits.fetches_per_day) {
        return loggedInUserIsPaying ? 'over-limit' : 'need-upgrade'
      }
      return 'ok'
    },
    [loggedInUserIsPaying, currentIsAutofetch, currentFetchInterval, lastKnownFetchesElsewhere, loggedInUser.limits.fetches_per_day]
  )

  const allowedCurrentFetchInterval = [...StandardIntervals, currentFetchInterval].reverse().find(i => findPricePoint(86400 / i) === 'ok') || StandardIntervals[0]

  React.useEffect(
    () => {
      if (submitting === null) return undefined
      if (submitting.failed) return undefined

      const { isAutofetch, fetchInterval } = submitting.data
      // "cancel" helps with multiple pending edits:
      //
      // User makes edit A: we submit it
      // User makes edit B: we submit it
      // Server responds to edit A: ignore this message! Don't setState()
      // Server responds to edit B: okay, we're happy
      let cancel = false
      let timeout = null
      async function go () {
        if (cancel) return
        try {
          await api.trySetStepAutofetch(stepSlug, isAutofetch, fetchInterval)
        } catch (err) {
          if (cancel) return

          if (err.serverError && err.serverError === 'AutofetchQuotaExceeded') {
            // If we got here, there's a race or bug in our logic or some-such.
            // Snap back to previous values. The user may notice this; let's
            // assume this doesn't happen often.
            setSubmitting(null)
          } else {
            setSubmitting({ ...submitting, failed: true })
          }
        }
        if (cancel) return
        // The server says ok, but it doesn't guarantee that the Redux state
        // is correct yet! Wait, then assume things have settled
        timeout = window.setTimeout(
          () => {
            timeout = null
            if (cancel) return
            setSubmitting(null)
          },
          delayMsAfterServerOk
        )
      }
      go()
      return () => {
        cancel = true
        if (timeout !== null) {
          window.clearTimeout(timeout)
          timeout = null
        }
      }
    },
    [api, stepSlug, submitting]
  )

  const handleClickRetry = React.useCallback(
    () => {
      const { failed, data, staleData } = submitting
      setSubmitting({ data, staleData, failed: false })
    },
    [submitting]
  )

  const handleToggleAutofetch = React.useCallback(
    ev => {
      setSubmitting({
        data: {
          isAutofetch: ev.target.checked,
          fetchInterval: allowedCurrentFetchInterval
        },
        staleData: {
          usage: lastKnownUsage,
          fetchesPerDay: lastKnownFetchesPerDayOnThisStep
        },
        failed: false
      })
    },
    [allowedCurrentFetchInterval, setSubmitting, lastKnownUsage, lastKnownFetchesPerDayOnThisStep]
  )

  const handleChangeFetchInterval = React.useCallback(
    ev => {
      setSubmitting({
        data: {
          isAutofetch: currentIsAutofetch,
          fetchInterval: +ev.target.value
        },
        staleData: {
          usage: lastKnownUsage,
          fetchesPerDay: lastKnownFetchesPerDayOnThisStep
        },
        failed: false
      })
    },
    [currentIsAutofetch, setSubmitting, lastKnownUsage, lastKnownFetchesPerDayOnThisStep]
  )

  const handleChangeEmailUpdates = React.useCallback(
    ev => {
      setEmailUpdates(ev.target.value)
    },
    [setEmailUpdates]
  )

  return (
    <Modal isOpen className='update-frequency-modal' toggle={onClose}>
      <ModalHeader>
        <Trans
          id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.header.title'
          comment='This should be all-caps for styling reasons'
        >
          AUTOMATIC UPDATES
        </Trans>
      </ModalHeader>
      <ModalBody>
        {submitting
          ? <Saving failed={submitting.failed || false} onClickRetry={handleClickRetry} />
          : null}
        <form
          className='autofetch'
          method='post'
          action='#'
          onSubmit={handleSubmit}
        >
          <AutofetchToggle
            checked={currentIsAutofetch}
            onChange={handleToggleAutofetch}
            pricePoint={currentIsAutofetch ? 'ok' : findPricePoint(1)}
          />
          <p className='description'>
            <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.auto.description'>
              Check for new data and update this workflow periodically.
            </Trans>
          </p>
          <label>
            <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.checkEvery.label'>
              Check for updates every
            </Trans>
            <select
              name='fetch-interval'
              value={allowedCurrentFetchInterval}
              onChange={handleChangeFetchInterval}
            >
              {StandardIntervals.includes(allowedCurrentFetchInterval)
                ? null
                : (
                  <IntervalOption
                    value={allowedCurrentFetchInterval}
                    pricePoint={findPricePoint(86400 / fetchInterval)}
                  />
                )}
              {StandardIntervals.map(value => (
                <IntervalOption
                  key={value}
                  value={value}
                  pricePoint={findPricePoint(86400 / value)}
                />
              ))}
            </select>
          </label>
        </form>

        <label className='email-updates'>
          <input
            type='checkbox'
            name='isEmailUpdates'
            checked={isEmailUpdates}
            onChange={handleChangeEmailUpdates}
          />
          <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.emailUpdates.label'>
            Email me when data changes
          </Trans>
        </label>
      </ModalBody>
      <ModalFooter>
        <div className='usage'>
          {t({
            id: 'js.params.Custom.VersionSelect.UpdateFrequencySelectModal.currentUsage',
            message: '{fetchesPerDay,number} of {limit,number} updates/day',
            values: {
              fetchesPerDay: lastKnownFetchesElsewhere + countFetchesPerDay(currentIsAutofetch, currentFetchInterval),
              limit: loggedInUser.limits.fetches_per_day
            }
          })}
        </div>
        {loggedInUserIsPaying
          ? null
          : (
            <a href="/settings/plan" target="_blank">
              <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.upgradeButton'>
                Upgrade
              </Trans>
            </a>)}
        <button
          type='button'
          className='close'
          title={t({
            id: 'js.params.Custom.VersionSelect.UpdateFrequencySelectModal.footer.closeButton.hoverText',
            message: 'Close'
          })}
          onClick={onClose}
        >
          <Trans id='js.params.Custom.VersionSelect.UpdateFrequencySelectModal.footer.closeButton'>
            Close
          </Trans>
        </button>
      </ModalFooter>
    </Modal>
  )
}
UpdateFrequencySelectModal.propTypes = {
  workflowId: propTypes.workflowId.isRequired,
  stepId: PropTypes.number.isRequired,
  stepSlug: PropTypes.string.isRequired,
  isAutofetch: PropTypes.bool.isRequired,
  fetchInterval: PropTypes.number.isRequired,
  isEmailUpdates: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired, // func() => undefined
  trySetAutofetch: PropTypes.func.isRequired, // func(stepSlug, isAutofetch, fetchInterval) => Promise[{}]
  setEmailUpdates: PropTypes.func.isRequired // func(isEmailUpdates) => undefined
}
