import httpOperations from './http-operations'

export const getDocument = async (templateName: string | undefined): Promise<any | null> => {
  if (!templateName) {
    return Promise.reject('templateName is required')
  }
  // const url = `/api/base/document/v1/template/${component}`;
  const url = `/api/v1/document-templates/code/${templateName}`

  return await httpOperations.get(url)
}

export const getRoutes = async (): Promise<any> => {
  const url = `/api/auth/privilege/v1/`
  return await httpOperations.get(url)
}
export const getMenus = async (): Promise<any> => {
  const url = `/api/v1/users/me/menus`
  return await httpOperations.get(url)
}

export const getOptions = async (): Promise<any> => {
  const url = `/api/v1/options`

  return await httpOperations.get(url)
}
