import {ServerBreakpoint, Variable} from './breakpoint'

/**
 * Convenience class that represents a StatusMessage.  It provides convenience
 * functions for interpreting and using the message.
 */
export class StatusMessage {
  /**
   * The parsed message or undefined if the status is not present or the message
   * could not be parsed.
   */
  message: string|undefined = undefined;

  constructor(private readonly parent: ServerBreakpoint|Variable) {
    this.message = this.parseMessage();
  }

  private parseMessage(): string|undefined {
    if (!this.parent.status?.description?.format) {
      return undefined;
    }

    // Get the formatting string such as "Failed to load '$0' which
    // helps debug $1"
    const formatMessage = this.parent.status.description;
    let formatString = formatMessage.format!;

    // Get the number of parameters to replace '$' prefixed vars.
    let totalParameters = 0;
    if (formatMessage.parameters) {
      totalParameters = formatMessage.parameters.length;
    }
    let dollarIndex;
    let outputString = '';

    // While we have remaining '$' place holders keep traversing the format
    // string.
    while ((dollarIndex = formatString.indexOf('$')) > -1) {
      // Add the first portion of the format string to the output.
      outputString += formatString.substr(0, dollarIndex);
      if (formatString.length > dollarIndex + 1) {
        // Get the parameters index value in the parameters list or a '$' if
        // the value is escaped.
        const nextChar = formatString.substr(dollarIndex + 1, 1);

        // Assumption is there are not more than 10 parameters.
        const intVal = Number(nextChar);
        if (nextChar === '$') {
          // The next character is a '$' this is an escaped character, be sure
          // to maintain the next '$'.
          outputString += '$';
          formatString = formatString.substr(dollarIndex + 2);
        } else if (
            !isNaN(intVal) && intVal < totalParameters &&
            formatMessage.parameters) {
          // Get the proper parameter for the index.
          outputString += formatMessage.parameters[intVal];
          formatString = formatString.substr(dollarIndex + 2);
        } else {
          // FormatMessage with too many arguments, unclear what to do from
          // the spec, will just keep it verbatim.
          outputString += '$';
          formatString = formatString.substr(dollarIndex + 1);
        }

      } else {
        // A '$' was the last value add it back.
        outputString += '$';
        formatString = '';
      }
    }

    // Add the remainder of the format string to the returned value.
    outputString += formatString;
    return outputString;
  }
}
