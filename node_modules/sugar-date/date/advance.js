'use strict';

var Sugar = require('sugar-core'),
    advanceDateWithArgs = require('./internal/advanceDateWithArgs');

Sugar.Date.defineInstanceWithArguments({

  'advance': function(d, args) {
    return advanceDateWithArgs(d, args, 1);
  }

});

module.exports = Sugar.Date.advance;