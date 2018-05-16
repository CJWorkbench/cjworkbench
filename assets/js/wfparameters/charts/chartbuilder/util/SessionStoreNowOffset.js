function getTzOffset() {
  var d = new Date();
  var fullMinutesAndSign = d.getTimezoneOffset()
  var positive = fullMinutesAndSign >= 0
  var fullMinutes = fullMinutesAndSign * (positive ? 1 : -1)
  var hours = Math.floor(fullMinutes / 60)
  var minutes = fullMinutes % 60

  var sign = positive ? '+' : '-'
  var hoursS = String(100 + hours).slice(1)
  var minutesS = String(100 + minutes).slice(1)
  return sign + hoursS + ':' + minutesS
}

module.exports = getTzOffset()
