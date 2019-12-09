/**
 * Tricks the parser of lingui so that we can hide certain constant values of messages from the translator.
 *
 * For example, for <Trans>The name of our account is {hideFromTrans('coolaccount')}</Trans>
 * the translator sees 'The name of our account is {0}',
 * while <Trans>The name of our account is {'coolaccount'}</Trans>
 * the translator would see 'The name of our account is coolaccount'
 */
export function hideFromTrans (string) {
  return string
}
