'use strict';

var Range = require('./internal/Range'),
    rangeIsValid = require('./internal/rangeIsValid'),
    defineOnPrototype = require('../common/internal/defineOnPrototype');

defineOnPrototype(Range, {

  'isValid': function() {
    return rangeIsValid(this);
  }

});

// This package does not export anything as it is
// simply defining "isValid" on Range.prototype.