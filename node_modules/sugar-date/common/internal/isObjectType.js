'use strict';

function isObjectType(obj, type) {
  return !!obj && (type || typeof obj) === 'object';
}

module.exports = isObjectType;