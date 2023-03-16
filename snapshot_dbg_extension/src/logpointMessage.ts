import {ServerBreakpoint} from './breakpoint';

/**
 * Convenience class that represents a Logpoint message and its expressions,
 * providing both the user version of the logpoint message, as well as the
 * server representation which uses a log message format and the extracte
 * expressions from the user version.
 */
export class LogpointMessage {
  /**
   * Builds a LogpointMessage from a user-supplied string.
   * E.g. input: "Hello there {name}"
   * @return logpoint message or undefined if the message could not be parsed.
   */
  static fromUserString(message: string): LogpointMessage
      | undefined {
    const parsedMessage = parseLogpointMessage(message);
    if (parsedMessage == undefined) {
      return undefined;
    }

    return new LogpointMessage(
        message, parsedMessage.formatMessage, parsedMessage.expressions);
  }

  /**
   * Builds a LogpointMessage from server breakpoint.
   */
  static fromBreakpoint(bp: ServerBreakpoint): LogpointMessage {
    const userMessage = parseMessageFormat(
        bp.logMessageFormat ?? '', bp.expressions ?? []);
    return new LogpointMessage(
        userMessage, bp.logMessageFormat ?? '', bp.expressions ?? []);
  }

  /**
   * Publicly available constructor, but it is expected that the factory methods
   * are used.  Members are publicly readable and are expected to be populated.
   *
   * For example:
   *                  userMessage         logMessageFormat   expressions
   * No expressions:  'Hello there'       'Hello there'      []
   * One expression:  'x = {x}",          'x = $0',          ['x']
   * Two expression:  'x = {x}, y = {y}'  'x = $0, y = $1',  ['x', 'y']
   *
   * @param userMessage The user supplied message with embedded expressions.
   * @param logMessageFormat The Snaphost Debugger format message with the
   *     expressions from the userMessage replaced by $0 etc.
   * @param expressions A possibly empty set of expressions to be evaluated and
   *     logged as part of the message.
   */
  private constructor(
      readonly userMessage: string,
      readonly logMessageFormat: string,
      readonly expressions: string[],
  ) {}
}

/**
 * Utility function that converts a user supplied log message with embedded
 * expressions into a Snapshot Debugger format string using $i and a list of
 * expressions.
 * @param logpointMessage The logpoint message as entered by the user, that
 *     needs to be converted to the debugger format message and expressions.
 *
 * For example:
 * Input: 'x = {x}'               Output: 'x = $0' ['x']
 * Input: 'x = {x{1}}, y = {foo}' Output: 'x = $0, y = $1' ['x{1}', 'foo']
 * Input: 'Hello $there {foo}'    Output: 'Hello $$there $0', ['foo']
 */
function parseLogpointMessage(logpointMessage: string):
    {formatMessage: string, expressions: string[]}|undefined {
  const expressions = [];
  let formatMessage = '';
  let logpointMessageIndex = 0;
  let expressionStartIndex = 0;
  let braceCount = 0;

  // Since '$'s have special meaning in the formatMessage, we escape
  // any pre-existing '$' by converting them to '$$'.
  // For the replace string in the replace function call, '$$' has
  // special meaning, and inserts a '$'. Note we should only apply the escaping
  // the portions of the string that will be part of the formatMessage. Any '$'
  // appearing in the expressions should be untouched.
  const escapeDollarSigns = (text: string): string => {
    return text.replace(/\$/g, '$$$$');
  };

  // Keep looking for the next brace character
  let braceResult = findNextBrace(logpointMessage, logpointMessageIndex);
  while (braceResult != undefined) {
    const braceIndex = braceResult.index;

    if (braceResult.character === '{') {
      if (braceCount === 0) {
        // Open brace outside an expression, start a new expression.
        formatMessage += escapeDollarSigns(
            logpointMessage.substring(logpointMessageIndex, braceIndex));
        expressionStartIndex = braceIndex + 1;
      }
      braceCount++;
    } else {
      if (braceCount === 0) {
        // Too many close braces, invalid format
        return undefined;
      } else if (braceCount === 1) {
        // Closing brace for an expression, add the expression
        formatMessage += `$${expressions.length}`;
        if (/\d/.test(logpointMessage[braceIndex + 1])) {
          // Add a space so {x}123 becomes $0 123 instead of $0123
          formatMessage += ' ';
        }
        expressions.push(
            logpointMessage.substring(expressionStartIndex, braceIndex));
      }

      braceCount--;
    }

    logpointMessageIndex = braceIndex + 1;
    braceResult = findNextBrace(logpointMessage, logpointMessageIndex);
  }

  if (braceCount !== 0) {
    // Unbalanced braces
    return undefined;
  }

  formatMessage +=
      escapeDollarSigns(logpointMessage.substring(logpointMessageIndex));
  return {formatMessage, expressions};
}

/**
 * Finds the index of the next '{' or '}' character or undefined if there are no
 * more brace characters.
 */
function findNextBrace(
    str: string, startIndex: number): {character: string, index: number}|undefined {
  const openIndex = str.indexOf('{', startIndex);
  const closeIndex = str.indexOf('}', startIndex);
  if (openIndex === -1 && closeIndex === -1) {
    return undefined;
  } else if (openIndex === -1) {
    return {character: '}', index: closeIndex};
  } else if (closeIndex === -1) {
    return {character: '{', index: openIndex};
  } else if (openIndex < closeIndex) {
    return {character: '{', index: openIndex};
  } else {
    return {character: '}', index: closeIndex};
  }
}

/**
 * Converts a Snapshot Debugger logpoint format string using $i with a list of
 * expressions to a log message with embedded expressions. It is expected the
 * input is valid, as it will be coming from actual breakpoints. If the
 * expressions provided don't match the format message exactly a string will
 * still be produced.
 *
 * @param messageFormat The logpoint format message where expressions have been
 * encoded with '$i''s.
 * @param expressions: The expressions array matching the encoded formatMessage.
 * @return A user friendly logpoint message.
 *
 * An example conversion:
 *  formatMessage: 'x = $0'
 *  expressions: ['x']
 *  logpointMessage: 'x = {x}'
 */
function parseMessageFormat(
    messageFormat: string, expressions: string[]): string {
  // Since '$'s have special meaning in the formatMessage, all $'s from the
  // user friendly logpoint message have been escaped in the format message by
  // converting them to '$$'. So we must un escape  them by converting them back
  // to '$'. Note, we should only apply the un escaping to the portions of the
  // string that are part of the format message. Any '$'s appearing in the
  // expressions should be untouched.
  //
  // For the replace string in the replace function call, '$$' has
  // special meaning, and inserts a '$'.
  const unEscapeDollarSigns = (text: string): string => {
    return text.replace(/\$\$/g, '$$');
  };

  // Regular expression that will match 1 or more dollar signs that are followed
  // by 1 or more digits.
  const expressionsPattern = /(\$+)(\d+)/g;

  // String.split with a regex will insert capture groups between the splits.
  // Here's an example:
  //   'Hello $1 $2, how are you?' =>
  //   ['Hello ', '$', '1', ' ', '$', '2', ', how are you?']
  //
  //   'abc$$0def' => ['abc', '$$', '0', 'def']

  const parts = messageFormat.split(expressionsPattern);
  let logpointMessage = '';

  // We go through the split array in groups of three, the part outside the
  // regex, the '$'s, and the digits.
  for (let i = 0; i < parts.length - 1; i += 3) {
    const dollars = parts[i + 1];
    const expression = expressions[Number(parts[i + 2])];

    // If there was an even number of dollar signs they are all escaped and
    // there is no expression to substitute in. Or if the expressions indexing
    // above failed, there is no expression to substitute in either.
    if (dollars.length % 2 === 0 || !expression) {
      logpointMessage += parts[i] + unEscapeDollarSigns(dollars) + parts[i + 2];
    } else {
      // Do the substring(1) to strip out the first dollar sign, it is no longer
      // needed.
      logpointMessage += parts[i] + unEscapeDollarSigns(dollars.substring(1));
      logpointMessage += '{' + expression + '}';
    }
  }

  // Could be a final part left to process if the for loop didn't consume it.
  if (parts.length % 3 !== 0) {
    logpointMessage += unEscapeDollarSigns(parts[parts.length - 1]);
  }

  return logpointMessage;
}
