'use strict';

var Sugar = require('sugar-core'),
    getUTCOffset = require('./internal/getUTCOffset');

Sugar.Date.defineInstance({

  'getUTCOffset': function(date, iso) {
    return getUTCOffset(date, iso);
  }

});

module.exports = Sugar.Date.getUTCOffset;