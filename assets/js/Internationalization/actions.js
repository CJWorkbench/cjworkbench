const SET_LOCALE = 'SET_LOCALE';

function reduceSetLocale(state, action){
  return {
    ...state,
    locale: action.locale
  };
}

export function setLocaleAction(locale){
  return {
    type: SET_LOCALE,
    locale: locale
  }
}

export const reducerFunctions = {
  [SET_LOCALE]: reduceSetLocale
}

export function localeReducer(state, action){
  if (action.type in reducerFunctions) {
    // Run a registered reducer
    return reducerFunctions[action.type](state, action)
  }
  
  return state;
}
