'use strict';

var isClass = require('./isClass'),
    isObjectType = require('./isObjectType'),
    hasOwnEnumeratedProperties = require('./hasOwnEnumeratedProperties'),
    hasValidPlainObjectPrototype = require('./hasValidPlainObjectPrototype');

function isPlainObject(obj, className) {
  return isObjectType(obj) &&
         isClass(obj, 'Object', className) &&
         hasValidPlainObjectPrototype(obj) &&
         hasOwnEnumeratedProperties(obj);
}

module.exports = isPlainObject;