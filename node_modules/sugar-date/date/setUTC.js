'use strict';

var Sugar = require('sugar-core'),
    _utc = require('../common/var/_utc');

Sugar.Date.defineInstance({

  'setUTC': function(date, on) {
    return _utc(date, on);
  }

});

module.exports = Sugar.Date.setUTC;