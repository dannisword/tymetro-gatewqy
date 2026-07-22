type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const levels: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/**
 * Determine log level based on environment or localStorage override
 * - development: debug
 * - stage/test: info
 * - production/formal: error
 */
const getLogLevel = (): LogLevel => {
  try {
    const localOverride = localStorage.getItem('LOG_LEVEL') as LogLevel;
    if (localOverride && levels[localOverride] !== undefined) {
      return localOverride;
    }
  } catch (e) {
    // Ignore localStorage access errors (e.g. security block)
  }

  // Read from .env file first
  const envLogLevel = import.meta.env.VITE_LOG_LEVEL as LogLevel;
  if (envLogLevel && levels[envLogLevel] !== undefined) {
    return envLogLevel;
  }

  const mode = import.meta.env.MODE;
  if (mode === 'development') {
    return 'debug';
  } else if (mode === 'stage' || mode === 'test') {
    return 'info';
  } else {
    return 'error';
  }
};

const shouldLog = (level: LogLevel): boolean => {
  const currentLevel = getLogLevel();
  return levels[level] >= levels[currentLevel];
};

export const logger = {
  debug(message: string, ...args: any[]) {
    if (shouldLog('debug')) {
      console.debug(`[DEBUG] ${message}`, ...args);
    }
  },
  info(message: string, ...args: any[]) {
    if (shouldLog('info')) {
      console.info(`[INFO] ${message}`, ...args);
    }
  },
  warn(message: string, ...args: any[]) {
    if (shouldLog('warn')) {
      console.warn(`[WARN] ${message}`, ...args);
    }
  },
  error(message: string, ...args: any[]) {
    if (shouldLog('error')) {
      console.error(`[ERROR] ${message}`, ...args);
    }
  }
};
