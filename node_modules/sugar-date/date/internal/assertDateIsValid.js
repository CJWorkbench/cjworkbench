'use strict';

var dateIsValid = require('./dateIsValid');

function assertDateIsValid(d) {
  if (!dateIsValid(d)) {
    throw new TypeError('Date is not valid');
  }
}

module.exports = assertDateIsValid;