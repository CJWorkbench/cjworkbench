'use strict';

var _dateOptions = require('../var/_dateOptions');

function getNewDate() {
  return _dateOptions('newDateInternal')();
}

module.exports = getNewDate;