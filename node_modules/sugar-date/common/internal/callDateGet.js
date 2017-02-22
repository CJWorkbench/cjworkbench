'use strict';

var _utc = require('../var/_utc');

function callDateGet(d, method) {
  return d['get' + (_utc(d) ? 'UTC' : '') + method]();
}

module.exports = callDateGet;