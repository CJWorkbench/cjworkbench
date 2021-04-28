import React from 'react'
import PropTypes from 'prop-types'
import DateGranularity from './DateGranularity'
import { Trans } from '@lingui/macro'

export default function DateGranularities (props) {
  const {
    isReadOnly,
    name,
    value,
    colnames,
    applyQuickFix
  } = props

  const handleClickUpgrade = React.useCallback(
    ev => {
      const byGranularity = {}
      colnames.forEach(colname => {
        const granularity = value[colname]
        if (granularity) {
          if (!(granularity in byGranularity)) {
            byGranularity[granularity] = []
          }
          byGranularity[granularity].push(colname)
        }
      })
      Object.keys(byGranularity).forEach(granularity => {
        const colnames = byGranularity[granularity]
        if ('STH'.indexOf(granularity) !== -1) {
          const operation = { S: 'startofsecond', T: 'startofminute', H: 'startofhour' }[granularity]
          colnames.forEach(colname => {
            applyQuickFix({
              type: 'prependStep',
              moduleSlug: 'timestampmath',
              partialParams: {
                operation,
                colname1: colname,
                outcolname: colname
              }
            })
          })
        } else {
          const unit = { D: 'day', W: 'week', M: 'month', Q: 'quarter', Y: 'year' }[granularity]
          applyQuickFix({
            type: 'prependStep',
            moduleSlug: 'converttimestamptodate',
            partialParams: { colnames, unit }
          })
        }
      })
    },
    [applyQuickFix, colnames, value]
  )

  return (
    <div className='date-granularities'>
      {!isReadOnly
        ? (
          <div className='date-granularities-deprecated'>
            <p>
              <Trans id='js.params.Custom.Groups.DateGranularities.deprecated'>
                The “Group Dates” option has changed. Please upgrade from Timestamps
                to Dates. Workbench will force-upgrade in January 2022.
              </Trans>
            </p>
            <button type='button' onClick={handleClickUpgrade}>
              <Trans id='js.params.Custom.Groups.DateGranularities.upgrade'>
                Upgrade to Dates
              </Trans>
            </button>
          </div>
          )
        : null}
      <ul>
        {colnames.map(colname => (
          <li key={colname}>
            <DateGranularity
              name={`${name}[${colname}]`}
              colname={colname}
              value={value[colname] || null}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
DateGranularities.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired, // for <select> names
  value: PropTypes.objectOf(PropTypes.oneOf('STHDWMQY'.split('')).isRequired).isRequired,
  colnames: PropTypes.arrayOf(PropTypes.string.isRequired), // null if unknown
  applyQuickFix: PropTypes.func.isRequired // func(newObject) => undefined
}
