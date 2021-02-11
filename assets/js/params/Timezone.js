/* globals fetch */
import { useState, useCallback, useEffect } from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from './util'

let timezonesPromiseSingleton = null
function fetchTimezones () {
  if (timezonesPromiseSingleton === null) {
    timezonesPromiseSingleton = (async () => {
      const response = await fetch('/jsdata/timezones.json')
      const data = await response.json()
      const timezones = data.timezones
      const aliases = {}
      timezones.forEach(({ id, aliases }) =>
        aliases.forEach(alias => {
          aliases[alias] = id
        })
      )
      return { timezones, aliases }
    })()
  }
  return timezonesPromiseSingleton
}

function cleanTimezoneId (value, { timezones, aliases }) {
  if (value in aliases) {
    return aliases[value]
  } else if (timezones.some(({ id }) => id === value)) {
    return value
  } else {
    return 'Etc/UTC' // fallback
  }
}

export default function TimezoneParam (props) {
  const { fieldId, label, name, value, isReadOnly, onChange } = props

  const [timezoneData, setTimezoneData] = useState(null)
  const handleChange = useCallback(
    ev => {
      onChange(ev.target.value)
    },
    [onChange]
  )

  useEffect(() => {
    fetchTimezones().then(setTimezoneData)
  }, [])

  const saneValue = timezoneData ? cleanTimezoneId(value, timezoneData) : value

  return (
    <>
      <MaybeLabel fieldId={fieldId} label={label} />
      <select
        name={name}
        id={fieldId}
        value={saneValue}
        onChange={handleChange}
        disabled={isReadOnly}
      >
        {timezoneData
          ? timezoneData.timezones.map(({ id, offset, name }) => (
            <option key={id} value={id}>
              {offset} {name}
            </option>
            ))
          : null}
      </select>
    </>
  )
}
TimezoneParam.propTypes = {
  fieldId: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired, // may be empty
  name: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired // onChange(ianaId) => undefined
}
