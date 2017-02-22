// Type definitions for Sugar v2.0.4
// Project: https://sugarjs.com/
// Definitions by: Andrew Plummer <plummer.andrew@gmail.com>

declare namespace sugarjs {

  type SugarDefaultChainable<RawValue> = Array.Chainable<any, RawValue> &
                                         Date.Chainable<RawValue> &
                                         Function.Chainable<RawValue> &
                                         Number.Chainable<RawValue> &
                                         Object.Chainable<RawValue> &
                                         RegExp.Chainable<RawValue> &
                                         String.Chainable<RawValue>;

  type NativeConstructor = ArrayConstructor |
                           DateConstructor |
                           FunctionConstructor |
                           NumberConstructor |
                           ObjectConstructor |
                           RegExpConstructor |
                           StringConstructor |
                           BooleanConstructor |
                           ErrorConstructor;

  interface Locale {
    addFormat(src:string, to?: Array<string>): void;
    getDuration(ms: number): string;
    getFirstDayOfWeek(): number;
    getFirstDayOfWeekYear(): number;
    getMonthName(n: number): string;
    getWeekdayName(n: number): string;
  }

  interface ExtendOptions {
    methods?: Array<string>;
    except?: Array<string|NativeConstructor>;
    namespaces?: Array<NativeConstructor>;
    enhance?: boolean;
    enhanceString?: boolean;
    enhanceArray?: boolean;
    objectPrototype?: boolean;
  }

  interface Sugar {
    (opts?: ExtendOptions): Sugar;
    createNamespace(name: string): SugarNamespace;
    extend(opts?: ExtendOptions): Sugar;
    Array: Array.Constructor;
    Date: Date.Constructor;
    Function: Function.Constructor;
    Number: Number.Constructor;
    Object: Object.Constructor;
    RegExp: RegExp.Constructor;
    String: String.Constructor;
  }

  interface SugarNamespace {
    alias(toName: string, from: string|Function): this;
    alias(toName: string, fn: undefined): this;
    defineInstance(methods: Object): this;
    defineInstance(methodName: string, methodFn: Function): this;
    defineInstanceAndStatic(methods: Object): this;
    defineInstanceAndStatic(methodName: string, methodFn: Function): this;
    defineInstancePolyfill(methods: Object): this;
    defineInstancePolyfill(methodName: string, methodFn: Function): this;
    defineInstanceWithArguments(methods: Object): this;
    defineInstanceWithArguments(methodName: string, methodFn: Function): this;
    defineStatic(methods: Object): this;
    defineStatic(methodName: string, methodFn: Function): this;
    defineStaticPolyfill(methods: Object): this;
    defineStaticPolyfill(methodName: string, methodFn: Function): this;
    defineStaticWithArguments(methods: Object): this;
    defineStaticWithArguments(methodName: string, methodFn: Function): this;
    extend(opts?: ExtendOptions): this;
  }

  namespace Array {

    type Chainable<T, RawValue> = ChainableBase<T, RawValue> & Object.ChainableBase<RawValue>;

    interface ChainableBase<T, RawValue> {
      raw: RawValue;
      valueOf: () => RawValue;
      toString: () => string;
      concat(...items: (T | T[])[]): SugarDefaultChainable<T[]>;
      concat(...items: T[][]): SugarDefaultChainable<T[]>;
      copyWithin(target: number, start: number, end?: number): SugarDefaultChainable<this>;
      every(callbackfn: (value: T, index: number, array: T[]) => boolean, thisArg?: any): SugarDefaultChainable<boolean>;
      fill(value: T, start?: number, end?: number): SugarDefaultChainable<this>;
      filter(callbackfn: (value: T, index: number, array: T[]) => any, thisArg?: any): SugarDefaultChainable<T[]>;
      find(predicate: (value: T, index: number, obj: Array<T>) => boolean, thisArg?: any): SugarDefaultChainable<T | undefined>;
      findIndex(predicate: (value: T, index: number, obj: Array<T>) => boolean, thisArg?: any): SugarDefaultChainable<number>;
      forEach(callbackfn: (value: T, index: number, array: T[]) => void, thisArg?: any): SugarDefaultChainable<void>;
      indexOf(searchElement: T, fromIndex?: number): SugarDefaultChainable<number>;
      join(separator?: string): SugarDefaultChainable<string>;
      lastIndexOf(searchElement: T, fromIndex?: number): SugarDefaultChainable<number>;
      map<U>(callbackfn: (value: T, index: number, array: T[]) => U, thisArg?: any): SugarDefaultChainable<U[]>;
      pop(): SugarDefaultChainable<T | undefined>;
      push(...items: T[]): SugarDefaultChainable<number>;
      reduce(callbackfn: (previousValue: T, currentValue: T, currentIndex: number, array: T[]) => T, initialValue?: T): SugarDefaultChainable<T>;
      reduce<U>(callbackfn: (previousValue: U, currentValue: T, currentIndex: number, array: T[]) => U, initialValue: U): SugarDefaultChainable<U>;
      reduceRight(callbackfn: (previousValue: T, currentValue: T, currentIndex: number, array: T[]) => T, initialValue?: T): SugarDefaultChainable<T>;
      reduceRight<U>(callbackfn: (previousValue: U, currentValue: T, currentIndex: number, array: T[]) => U, initialValue: U): SugarDefaultChainable<U>;
      reverse(): SugarDefaultChainable<T[]>;
      shift(): SugarDefaultChainable<T | undefined>;
      slice(start?: number, end?: number): SugarDefaultChainable<T[]>;
      some(callbackfn: (value: T, index: number, array: T[]) => boolean, thisArg?: any): SugarDefaultChainable<boolean>;
      sort(compareFn?: (a: T, b: T) => number): SugarDefaultChainable<this>;
      splice(start: number): SugarDefaultChainable<T[]>;
      splice(start: number, deleteCount: number, ...items: T[]): SugarDefaultChainable<T[]>;
      toLocaleString(): SugarDefaultChainable<string>;
      unshift(...items: T[]): SugarDefaultChainable<number>;
    }

  }

  namespace Date {

    type Chainable<RawValue> = ChainableBase<RawValue> & Object.ChainableBase<RawValue>;

    interface Constructor extends SugarNamespace {
      (d?: string|number|Date, options?: DateCreateOptions): Chainable<Date>;
      new(d?: string|number|Date, options?: DateCreateOptions): Chainable<Date>;
      addLocale(localeCode: string, def: Object): Locale;
      create(d?: string|number|Date, options?: DateCreateOptions): Date;
      getAllLocaleCodes(): string[];
      getAllLocales(): Array<Locale>;
      getLocale(localeCode?: string): Locale;
      removeLocale(localeCode: string): Locale;
      setLocale(localeCode: string): Locale;
      addDays(instance: Date, n: number, reset?: boolean): Date;
      addHours(instance: Date, n: number, reset?: boolean): Date;
      addMilliseconds(instance: Date, n: number, reset?: boolean): Date;
      addMinutes(instance: Date, n: number, reset?: boolean): Date;
      addMonths(instance: Date, n: number, reset?: boolean): Date;
      addSeconds(instance: Date, n: number, reset?: boolean): Date;
      addWeeks(instance: Date, n: number, reset?: boolean): Date;
      addYears(instance: Date, n: number, reset?: boolean): Date;
      advance(instance: Date, set: string|Object, reset?: boolean): Date;
      advance(instance: Date, milliseconds: number): Date;
      advance(instance: Date, year: number, month: number, day?: number, hour?: number, minute?: number, second?: number, millliseconds?: undefined): Date;
      beginningOfDay(instance: Date, localeCode?: string): Date;
      beginningOfISOWeek(instance: Date): Date;
      beginningOfMonth(instance: Date, localeCode?: string): Date;
      beginningOfWeek(instance: Date, localeCode?: string): Date;
      beginningOfYear(instance: Date, localeCode?: string): Date;
      clone(instance: Date): Date;
      daysAgo(instance: Date): number;
      daysFromNow(instance: Date): number;
      daysInMonth(instance: Date): number;
      daysSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      daysUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      endOfDay(instance: Date, localeCode?: string): Date;
      endOfISOWeek(instance: Date): Date;
      endOfMonth(instance: Date, localeCode?: string): Date;
      endOfWeek(instance: Date, localeCode?: string): Date;
      endOfYear(instance: Date, localeCode?: string): Date;
      format(instance: Date, f?: string, localeCode?: string): string;
      full(instance: Date, localeCode?: string): string;
      get(instance: Date, d: string|number|Date, options?: DateCreateOptions): Date;
      getISOWeek(instance: Date): number;
      getUTCOffset(instance: Date, iso?: boolean): string;
      getUTCWeekday(instance: Date): number;
      getWeekday(instance: Date): number;
      hoursAgo(instance: Date): number;
      hoursFromNow(instance: Date): number;
      hoursSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      hoursUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      is(instance: Date, d: string|number|Date, margin?: number): boolean;
      isAfter(instance: Date, d: string|number|Date, margin?: number): boolean;
      isBefore(instance: Date, d: string|number|Date, margin?: number): boolean;
      isBetween(instance: Date, d1: string|number|Date, d2: string|number|Date, margin?: number): boolean;
      isFriday(instance: Date): boolean;
      isFuture(instance: Date): boolean;
      isLastMonth(instance: Date, localeCode?: string): boolean;
      isLastWeek(instance: Date, localeCode?: string): boolean;
      isLastYear(instance: Date, localeCode?: string): boolean;
      isLeapYear(instance: Date): boolean;
      isMonday(instance: Date): boolean;
      isNextMonth(instance: Date, localeCode?: string): boolean;
      isNextWeek(instance: Date, localeCode?: string): boolean;
      isNextYear(instance: Date, localeCode?: string): boolean;
      isPast(instance: Date): boolean;
      isSaturday(instance: Date): boolean;
      isSunday(instance: Date): boolean;
      isThisMonth(instance: Date, localeCode?: string): boolean;
      isThisWeek(instance: Date, localeCode?: string): boolean;
      isThisYear(instance: Date, localeCode?: string): boolean;
      isThursday(instance: Date): boolean;
      isToday(instance: Date): boolean;
      isTomorrow(instance: Date): boolean;
      isTuesday(instance: Date): boolean;
      isUTC(instance: Date): boolean;
      isValid(instance: Date): boolean;
      isWednesday(instance: Date): boolean;
      isWeekday(instance: Date): boolean;
      isWeekend(instance: Date): boolean;
      isYesterday(instance: Date): boolean;
      iso(instance: Date): string;
      long(instance: Date, localeCode?: string): string;
      medium(instance: Date, localeCode?: string): string;
      millisecondsAgo(instance: Date): number;
      millisecondsFromNow(instance: Date): number;
      millisecondsSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      millisecondsUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      minutesAgo(instance: Date): number;
      minutesFromNow(instance: Date): number;
      minutesSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      minutesUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      monthsAgo(instance: Date): number;
      monthsFromNow(instance: Date): number;
      monthsSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      monthsUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      relative(instance: Date, localeCode?: string, fn?: (num: number, unit: number, ms: number, loc: Locale) => string): string;
      relative(instance: Date, fn?: (num: number, unit: number, ms: number, loc: Locale) => string): string;
      relativeTo(instance: Date, d: string|number|Date, localeCode?: string): string;
      reset(instance: Date, unit?: string, localeCode?: string): Date;
      rewind(instance: Date, set: string|Object, reset?: boolean): Date;
      rewind(instance: Date, milliseconds: number): Date;
      rewind(instance: Date, year: number, month: number, day?: number, hour?: number, minute?: number, second?: number, millliseconds?: undefined): Date;
      secondsAgo(instance: Date): number;
      secondsFromNow(instance: Date): number;
      secondsSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      secondsUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      set(instance: Date, set: Object, reset?: boolean): Date;
      set(instance: Date, milliseconds: number): Date;
      set(instance: Date, year: number, month: number, day?: number, hour?: number, minute?: number, second?: number, millliseconds?: undefined): Date;
      setISOWeek(instance: Date, num: number): void;
      setUTC(instance: Date, on?: boolean): Date;
      setWeekday(instance: Date, dow: number): void;
      short(instance: Date, localeCode?: string): string;
      weeksAgo(instance: Date): number;
      weeksFromNow(instance: Date): number;
      weeksSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      weeksUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      yearsAgo(instance: Date): number;
      yearsFromNow(instance: Date): number;
      yearsSince(instance: Date, d: string|number|Date, options?: DateCreateOptions): number;
      yearsUntil(instance: Date, d?: string|number|Date, options?: DateCreateOptions): number;
      getOption<T>(name: string): T;
      setOption(name: string, value: any): void;
      setOption(options: DateOptions): void;
    }

    interface ChainableBase<RawValue> {
      raw: RawValue;
      valueOf: () => RawValue;
      toString: () => string;
      addDays(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      addHours(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      addMilliseconds(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      addMinutes(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      addMonths(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      addSeconds(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      addWeeks(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      addYears(n: number, reset?: boolean): SugarDefaultChainable<Date>;
      advance(set: string|Object, reset?: boolean): SugarDefaultChainable<Date>;
      advance(milliseconds: number): SugarDefaultChainable<Date>;
      advance(year: number, month: number, day?: number, hour?: number, minute?: number, second?: number, millliseconds?: undefined): SugarDefaultChainable<Date>;
      beginningOfDay(localeCode?: string): SugarDefaultChainable<Date>;
      beginningOfISOWeek(): SugarDefaultChainable<Date>;
      beginningOfMonth(localeCode?: string): SugarDefaultChainable<Date>;
      beginningOfWeek(localeCode?: string): SugarDefaultChainable<Date>;
      beginningOfYear(localeCode?: string): SugarDefaultChainable<Date>;
      clone(): SugarDefaultChainable<Date>;
      daysAgo(): SugarDefaultChainable<number>;
      daysFromNow(): SugarDefaultChainable<number>;
      daysInMonth(): SugarDefaultChainable<number>;
      daysSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      daysUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      endOfDay(localeCode?: string): SugarDefaultChainable<Date>;
      endOfISOWeek(): SugarDefaultChainable<Date>;
      endOfMonth(localeCode?: string): SugarDefaultChainable<Date>;
      endOfWeek(localeCode?: string): SugarDefaultChainable<Date>;
      endOfYear(localeCode?: string): SugarDefaultChainable<Date>;
      format(f?: string, localeCode?: string): SugarDefaultChainable<string>;
      full(localeCode?: string): SugarDefaultChainable<string>;
      get(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<Date>;
      getISOWeek(): SugarDefaultChainable<number>;
      getUTCOffset(iso?: boolean): SugarDefaultChainable<string>;
      getUTCWeekday(): SugarDefaultChainable<number>;
      getWeekday(): SugarDefaultChainable<number>;
      hoursAgo(): SugarDefaultChainable<number>;
      hoursFromNow(): SugarDefaultChainable<number>;
      hoursSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      hoursUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      is(d: string|number|Date, margin?: number): SugarDefaultChainable<boolean>;
      isAfter(d: string|number|Date, margin?: number): SugarDefaultChainable<boolean>;
      isBefore(d: string|number|Date, margin?: number): SugarDefaultChainable<boolean>;
      isBetween(d1: string|number|Date, d2: string|number|Date, margin?: number): SugarDefaultChainable<boolean>;
      isFriday(): SugarDefaultChainable<boolean>;
      isFuture(): SugarDefaultChainable<boolean>;
      isLastMonth(localeCode?: string): SugarDefaultChainable<boolean>;
      isLastWeek(localeCode?: string): SugarDefaultChainable<boolean>;
      isLastYear(localeCode?: string): SugarDefaultChainable<boolean>;
      isLeapYear(): SugarDefaultChainable<boolean>;
      isMonday(): SugarDefaultChainable<boolean>;
      isNextMonth(localeCode?: string): SugarDefaultChainable<boolean>;
      isNextWeek(localeCode?: string): SugarDefaultChainable<boolean>;
      isNextYear(localeCode?: string): SugarDefaultChainable<boolean>;
      isPast(): SugarDefaultChainable<boolean>;
      isSaturday(): SugarDefaultChainable<boolean>;
      isSunday(): SugarDefaultChainable<boolean>;
      isThisMonth(localeCode?: string): SugarDefaultChainable<boolean>;
      isThisWeek(localeCode?: string): SugarDefaultChainable<boolean>;
      isThisYear(localeCode?: string): SugarDefaultChainable<boolean>;
      isThursday(): SugarDefaultChainable<boolean>;
      isToday(): SugarDefaultChainable<boolean>;
      isTomorrow(): SugarDefaultChainable<boolean>;
      isTuesday(): SugarDefaultChainable<boolean>;
      isUTC(): SugarDefaultChainable<boolean>;
      isValid(): SugarDefaultChainable<boolean>;
      isWednesday(): SugarDefaultChainable<boolean>;
      isWeekday(): SugarDefaultChainable<boolean>;
      isWeekend(): SugarDefaultChainable<boolean>;
      isYesterday(): SugarDefaultChainable<boolean>;
      iso(): SugarDefaultChainable<string>;
      long(localeCode?: string): SugarDefaultChainable<string>;
      medium(localeCode?: string): SugarDefaultChainable<string>;
      millisecondsAgo(): SugarDefaultChainable<number>;
      millisecondsFromNow(): SugarDefaultChainable<number>;
      millisecondsSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      millisecondsUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      minutesAgo(): SugarDefaultChainable<number>;
      minutesFromNow(): SugarDefaultChainable<number>;
      minutesSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      minutesUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      monthsAgo(): SugarDefaultChainable<number>;
      monthsFromNow(): SugarDefaultChainable<number>;
      monthsSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      monthsUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      relative(localeCode?: string, fn?: (num: number, unit: number, ms: number, loc: Locale) => SugarDefaultChainable<string>): SugarDefaultChainable<string>;
      relative(fn?: (num: number, unit: number, ms: number, loc: Locale) => SugarDefaultChainable<string>): SugarDefaultChainable<string>;
      relativeTo(d: string|number|Date, localeCode?: string): SugarDefaultChainable<string>;
      reset(unit?: string, localeCode?: string): SugarDefaultChainable<Date>;
      rewind(set: string|Object, reset?: boolean): SugarDefaultChainable<Date>;
      rewind(milliseconds: number): SugarDefaultChainable<Date>;
      rewind(year: number, month: number, day?: number, hour?: number, minute?: number, second?: number, millliseconds?: undefined): SugarDefaultChainable<Date>;
      secondsAgo(): SugarDefaultChainable<number>;
      secondsFromNow(): SugarDefaultChainable<number>;
      secondsSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      secondsUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      set(set: Object, reset?: boolean): SugarDefaultChainable<Date>;
      set(milliseconds: number): SugarDefaultChainable<Date>;
      set(year: number, month: number, day?: number, hour?: number, minute?: number, second?: number, millliseconds?: undefined): SugarDefaultChainable<Date>;
      setISOWeek(num: number): SugarDefaultChainable<void>;
      setUTC(on?: boolean): SugarDefaultChainable<Date>;
      setWeekday(dow: number): SugarDefaultChainable<void>;
      short(localeCode?: string): SugarDefaultChainable<string>;
      weeksAgo(): SugarDefaultChainable<number>;
      weeksFromNow(): SugarDefaultChainable<number>;
      weeksSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      weeksUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      yearsAgo(): SugarDefaultChainable<number>;
      yearsFromNow(): SugarDefaultChainable<number>;
      yearsSince(d: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      yearsUntil(d?: string|number|Date, options?: DateCreateOptions): SugarDefaultChainable<number>;
      getDate(): SugarDefaultChainable<number>;
      getDay(): SugarDefaultChainable<number>;
      getFullYear(): SugarDefaultChainable<number>;
      getHours(): SugarDefaultChainable<number>;
      getMilliseconds(): SugarDefaultChainable<number>;
      getMinutes(): SugarDefaultChainable<number>;
      getMonth(): SugarDefaultChainable<number>;
      getSeconds(): SugarDefaultChainable<number>;
      getTime(): SugarDefaultChainable<number>;
      getTimezoneOffset(): SugarDefaultChainable<number>;
      getUTCDate(): SugarDefaultChainable<number>;
      getUTCDay(): SugarDefaultChainable<number>;
      getUTCFullYear(): SugarDefaultChainable<number>;
      getUTCHours(): SugarDefaultChainable<number>;
      getUTCMilliseconds(): SugarDefaultChainable<number>;
      getUTCMinutes(): SugarDefaultChainable<number>;
      getUTCMonth(): SugarDefaultChainable<number>;
      getUTCSeconds(): SugarDefaultChainable<number>;
      setDate(date: number): SugarDefaultChainable<number>;
      setFullYear(year: number, month?: number, date?: number): SugarDefaultChainable<number>;
      setHours(hours: number, min?: number, sec?: number, ms?: number): SugarDefaultChainable<number>;
      setMilliseconds(ms: number): SugarDefaultChainable<number>;
      setMinutes(min: number, sec?: number, ms?: number): SugarDefaultChainable<number>;
      setMonth(month: number, date?: number): SugarDefaultChainable<number>;
      setSeconds(sec: number, ms?: number): SugarDefaultChainable<number>;
      setTime(time: number): SugarDefaultChainable<number>;
      setUTCDate(date: number): SugarDefaultChainable<number>;
      setUTCFullYear(year: number, month?: number, date?: number): SugarDefaultChainable<number>;
      setUTCHours(hours: number, min?: number, sec?: number, ms?: number): SugarDefaultChainable<number>;
      setUTCMilliseconds(ms: number): SugarDefaultChainable<number>;
      setUTCMinutes(min: number, sec?: number, ms?: number): SugarDefaultChainable<number>;
      setUTCMonth(month: number, date?: number): SugarDefaultChainable<number>;
      setUTCSeconds(sec: number, ms?: number): SugarDefaultChainable<number>;
      toDateString(): SugarDefaultChainable<string>;
      toISOString(): SugarDefaultChainable<string>;
      toJSON(key?: any): SugarDefaultChainable<string>;
      toLocaleDateString(locales?: string | string[], options?: Intl.DateTimeFormatOptions): SugarDefaultChainable<string>;
      toLocaleDateString(): SugarDefaultChainable<string>;
      toLocaleString(): SugarDefaultChainable<string>;
      toLocaleString(locales?: string | string[], options?: Intl.DateTimeFormatOptions): SugarDefaultChainable<string>;
      toLocaleTimeString(): SugarDefaultChainable<string>;
      toLocaleTimeString(locales?: string | string[], options?: Intl.DateTimeFormatOptions): SugarDefaultChainable<string>;
      toTimeString(): SugarDefaultChainable<string>;
      toUTCString(): SugarDefaultChainable<string>;
    }

    interface DateOptions {
      newDateInternal: Function;
    }

    interface DateCreateOptions {
      locale?: string;
      past?: boolean;
      future?: boolean;
      fromUTC?: boolean;
      setUTC?: boolean;
      clone?: boolean;
      params?: Object;
    }

  }

  namespace Function {

    type Chainable<RawValue> = ChainableBase<RawValue> & Object.ChainableBase<RawValue>;

    interface ChainableBase<RawValue> {
      raw: RawValue;
      valueOf: () => RawValue;
      toString: () => string;
      apply(thisArg: any, argArray?: any): SugarDefaultChainable<any>;
      bind(thisArg: any, ...argArray: any[]): SugarDefaultChainable<any>;
      call(thisArg: any, ...argArray: any[]): SugarDefaultChainable<any>;
    }

  }

  namespace Number {

    type Chainable<RawValue> = ChainableBase<RawValue> & Object.ChainableBase<RawValue>;

    interface Constructor extends SugarNamespace {
      day(instance: number): number;
      dayAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      dayAgo(instance: number): Date;
      dayBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      dayFromNow(instance: number): Date;
      days(instance: number): number;
      daysAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      daysAgo(instance: number): Date;
      daysBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      daysFromNow(instance: number): Date;
      duration(instance: number, localeCode?: string): string;
      hour(instance: number): number;
      hourAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      hourAgo(instance: number): Date;
      hourBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      hourFromNow(instance: number): Date;
      hours(instance: number): number;
      hoursAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      hoursAgo(instance: number): Date;
      hoursBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      hoursFromNow(instance: number): Date;
      millisecond(instance: number): number;
      millisecondAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      millisecondAgo(instance: number): Date;
      millisecondBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      millisecondFromNow(instance: number): Date;
      milliseconds(instance: number): number;
      millisecondsAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      millisecondsAgo(instance: number): Date;
      millisecondsBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      millisecondsFromNow(instance: number): Date;
      minute(instance: number): number;
      minuteAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      minuteAgo(instance: number): Date;
      minuteBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      minuteFromNow(instance: number): Date;
      minutes(instance: number): number;
      minutesAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      minutesAgo(instance: number): Date;
      minutesBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      minutesFromNow(instance: number): Date;
      month(instance: number): number;
      monthAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      monthAgo(instance: number): Date;
      monthBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      monthFromNow(instance: number): Date;
      months(instance: number): number;
      monthsAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      monthsAgo(instance: number): Date;
      monthsBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      monthsFromNow(instance: number): Date;
      second(instance: number): number;
      secondAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      secondAgo(instance: number): Date;
      secondBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      secondFromNow(instance: number): Date;
      seconds(instance: number): number;
      secondsAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      secondsAgo(instance: number): Date;
      secondsBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      secondsFromNow(instance: number): Date;
      week(instance: number): number;
      weekAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      weekAgo(instance: number): Date;
      weekBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      weekFromNow(instance: number): Date;
      weeks(instance: number): number;
      weeksAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      weeksAgo(instance: number): Date;
      weeksBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      weeksFromNow(instance: number): Date;
      year(instance: number): number;
      yearAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      yearAgo(instance: number): Date;
      yearBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      yearFromNow(instance: number): Date;
      years(instance: number): number;
      yearsAfter(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      yearsAgo(instance: number): Date;
      yearsBefore(instance: number, d: string|number|Date, options?: Date.DateCreateOptions): Date;
      yearsFromNow(instance: number): Date;
    }

    interface ChainableBase<RawValue> {
      raw: RawValue;
      valueOf: () => RawValue;
      toString: () => string;
      day(): SugarDefaultChainable<number>;
      dayAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      dayAgo(): SugarDefaultChainable<Date>;
      dayBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      dayFromNow(): SugarDefaultChainable<Date>;
      days(): SugarDefaultChainable<number>;
      daysAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      daysAgo(): SugarDefaultChainable<Date>;
      daysBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      daysFromNow(): SugarDefaultChainable<Date>;
      duration(localeCode?: string): SugarDefaultChainable<string>;
      hour(): SugarDefaultChainable<number>;
      hourAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      hourAgo(): SugarDefaultChainable<Date>;
      hourBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      hourFromNow(): SugarDefaultChainable<Date>;
      hours(): SugarDefaultChainable<number>;
      hoursAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      hoursAgo(): SugarDefaultChainable<Date>;
      hoursBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      hoursFromNow(): SugarDefaultChainable<Date>;
      millisecond(): SugarDefaultChainable<number>;
      millisecondAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      millisecondAgo(): SugarDefaultChainable<Date>;
      millisecondBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      millisecondFromNow(): SugarDefaultChainable<Date>;
      milliseconds(): SugarDefaultChainable<number>;
      millisecondsAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      millisecondsAgo(): SugarDefaultChainable<Date>;
      millisecondsBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      millisecondsFromNow(): SugarDefaultChainable<Date>;
      minute(): SugarDefaultChainable<number>;
      minuteAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      minuteAgo(): SugarDefaultChainable<Date>;
      minuteBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      minuteFromNow(): SugarDefaultChainable<Date>;
      minutes(): SugarDefaultChainable<number>;
      minutesAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      minutesAgo(): SugarDefaultChainable<Date>;
      minutesBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      minutesFromNow(): SugarDefaultChainable<Date>;
      month(): SugarDefaultChainable<number>;
      monthAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      monthAgo(): SugarDefaultChainable<Date>;
      monthBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      monthFromNow(): SugarDefaultChainable<Date>;
      months(): SugarDefaultChainable<number>;
      monthsAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      monthsAgo(): SugarDefaultChainable<Date>;
      monthsBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      monthsFromNow(): SugarDefaultChainable<Date>;
      second(): SugarDefaultChainable<number>;
      secondAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      secondAgo(): SugarDefaultChainable<Date>;
      secondBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      secondFromNow(): SugarDefaultChainable<Date>;
      seconds(): SugarDefaultChainable<number>;
      secondsAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      secondsAgo(): SugarDefaultChainable<Date>;
      secondsBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      secondsFromNow(): SugarDefaultChainable<Date>;
      week(): SugarDefaultChainable<number>;
      weekAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      weekAgo(): SugarDefaultChainable<Date>;
      weekBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      weekFromNow(): SugarDefaultChainable<Date>;
      weeks(): SugarDefaultChainable<number>;
      weeksAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      weeksAgo(): SugarDefaultChainable<Date>;
      weeksBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      weeksFromNow(): SugarDefaultChainable<Date>;
      year(): SugarDefaultChainable<number>;
      yearAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      yearAgo(): SugarDefaultChainable<Date>;
      yearBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      yearFromNow(): SugarDefaultChainable<Date>;
      years(): SugarDefaultChainable<number>;
      yearsAfter(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      yearsAgo(): SugarDefaultChainable<Date>;
      yearsBefore(d: string|number|Date, options?: Date.DateCreateOptions): SugarDefaultChainable<Date>;
      yearsFromNow(): SugarDefaultChainable<Date>;
      toExponential(fractionDigits?: number): SugarDefaultChainable<string>;
      toFixed(fractionDigits?: number): SugarDefaultChainable<string>;
      toLocaleString(locales?: string | string[], options?: Intl.NumberFormatOptions): SugarDefaultChainable<string>;
      toPrecision(precision?: number): SugarDefaultChainable<string>;
    }

  }

  namespace Object {

    type Chainable<RawValue> = ChainableBase<RawValue>;

    interface ChainableBase<RawValue> {
      raw: RawValue;
      valueOf: () => RawValue;
      toString: () => string;
    }

  }

  namespace RegExp {

    type Chainable<RawValue> = ChainableBase<RawValue> & Object.ChainableBase<RawValue>;

    interface ChainableBase<RawValue> {
      raw: RawValue;
      valueOf: () => RawValue;
      toString: () => string;
      exec(string: string): SugarDefaultChainable<RegExpExecArray | null>;
      test(string: string): SugarDefaultChainable<boolean>;
    }

  }

  namespace String {

    type Chainable<RawValue> = ChainableBase<RawValue> & Object.ChainableBase<RawValue>;

    interface ChainableBase<RawValue> {
      raw: RawValue;
      valueOf: () => RawValue;
      toString: () => string;
      anchor(name: string): SugarDefaultChainable<string>;
      big(): SugarDefaultChainable<string>;
      blink(): SugarDefaultChainable<string>;
      bold(): SugarDefaultChainable<string>;
      charAt(pos: number): SugarDefaultChainable<string>;
      charCodeAt(index: number): SugarDefaultChainable<number>;
      codePointAt(pos: number): SugarDefaultChainable<number | undefined>;
      concat(...strings: string[]): SugarDefaultChainable<string>;
      endsWith(searchString: string, endPosition?: number): SugarDefaultChainable<boolean>;
      fixed(): SugarDefaultChainable<string>;
      fontcolor(color: string): SugarDefaultChainable<string>;
      fontsize(size: number): SugarDefaultChainable<string>;
      fontsize(size: string): SugarDefaultChainable<string>;
      includes(searchString: string, position?: number): SugarDefaultChainable<boolean>;
      indexOf(searchString: string, position?: number): SugarDefaultChainable<number>;
      italics(): SugarDefaultChainable<string>;
      lastIndexOf(searchString: string, position?: number): SugarDefaultChainable<number>;
      link(url: string): SugarDefaultChainable<string>;
      localeCompare(that: string): SugarDefaultChainable<number>;
      localeCompare(that: string, locales?: string | string[], options?: Intl.CollatorOptions): SugarDefaultChainable<number>;
      match(regexp: RegExp): SugarDefaultChainable<RegExpMatchArray | null>;
      match(regexp: string): SugarDefaultChainable<RegExpMatchArray | null>;
      normalize(form?: string): SugarDefaultChainable<string>;
      normalize(form: "NFC" | "NFD" | "NFKC" | "NFKD"): SugarDefaultChainable<string>;
      repeat(count: number): SugarDefaultChainable<string>;
      replace(searchValue: string, replaceValue: string): SugarDefaultChainable<string>;
      replace(searchValue: string, replacer: (substring: string, ...args: any[]) => string): SugarDefaultChainable<string>;
      replace(searchValue: RegExp, replaceValue: string): SugarDefaultChainable<string>;
      replace(searchValue: RegExp, replacer: (substring: string, ...args: any[]) => string): SugarDefaultChainable<string>;
      search(regexp: RegExp): SugarDefaultChainable<number>;
      search(regexp: string): SugarDefaultChainable<number>;
      slice(start?: number, end?: number): SugarDefaultChainable<string>;
      small(): SugarDefaultChainable<string>;
      split(separator: string, limit?: number): SugarDefaultChainable<string[]>;
      split(separator: RegExp, limit?: number): SugarDefaultChainable<string[]>;
      startsWith(searchString: string, position?: number): SugarDefaultChainable<boolean>;
      strike(): SugarDefaultChainable<string>;
      sub(): SugarDefaultChainable<string>;
      substr(from: number, length?: number): SugarDefaultChainable<string>;
      substring(start: number, end?: number): SugarDefaultChainable<string>;
      sup(): SugarDefaultChainable<string>;
      toLocaleLowerCase(): SugarDefaultChainable<string>;
      toLocaleUpperCase(): SugarDefaultChainable<string>;
      toLowerCase(): SugarDefaultChainable<string>;
      toUpperCase(): SugarDefaultChainable<string>;
      trim(): SugarDefaultChainable<string>;
    }

  }

}

declare module "sugar" {
  const Sugar: sugarjs.Sugar;
  export = Sugar;
}

declare var Sugar: sugarjs.Sugar;