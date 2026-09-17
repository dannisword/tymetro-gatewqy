export interface GitVersionInfo {
  commit: string;
  branch: string;
  date: string;
}

export interface AppVersionInfo {
  version: string;
  commit: string;
  branch: string;
  date: string;
}

export const frontendVersionInfo: AppVersionInfo = {
  version: typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '1.0.0',
  commit: typeof __GIT_COMMIT__ !== 'undefined' ? __GIT_COMMIT__ : 'unknown',
  branch: typeof __GIT_BRANCH__ !== 'undefined' ? __GIT_BRANCH__ : 'unknown',
  date: typeof __GIT_DATE__ !== 'undefined' ? __GIT_DATE__ : '',
};
