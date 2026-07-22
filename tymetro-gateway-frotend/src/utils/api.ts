import httpOperations from "./http-operations";

export const getConfigsByType = async (type: string): Promise<any> => {
    const url = `/api/v1/configs/type/${type}`
    return await httpOperations.get(url)
}

export const updateConfig = async (configId: number, config: any): Promise<any> => {
    const url = `/api/v1/configs/${configId}`
    return await httpOperations.put(url, config)
}

export const getConfigsListByType = async (type: string): Promise<any> => {
    const url = `/api/v1/configs?configType=${type}&pageSize=100`
    return await httpOperations.get(url)
}

export const upsertConfig = async (config: any): Promise<any> => {
    const url = `/api/v1/configs/upsert`
    return await httpOperations.post(url, config)
}

export const getSchedulesList = async (params?: any): Promise<any> => {
    return await httpOperations.get('/api/v1/schedules', params)
}

export const getScheduleById = async (id: number): Promise<any> => {
    return await httpOperations.get(`/api/v1/schedules/${id}`)
}

export const createSchedule = async (data: any): Promise<any> => {
    return await httpOperations.post('/api/v1/schedules', data)
}

export const updateSchedule = async (id: number, data: any): Promise<any> => {
    return await httpOperations.put(`/api/v1/schedules/${id}`, data)
}

export const deleteSchedule = async (id: number): Promise<any> => {
    return await httpOperations.delete(`/api/v1/schedules/${id}`)
}

export const getModbusRegisters = async (params?: any): Promise<any> => {
    return await httpOperations.get('/api/v1/sensors', params)
}

export const getModbusRegisterById = async (id: number): Promise<any> => {
    return await httpOperations.get(`/api/v1/sensors/${id}`)
}

export const createModbusRegister = async (data: any): Promise<any> => {
    return await httpOperations.post('/api/v1/sensors', data)
}

export const updateModbusRegister = async (id: number, data: any): Promise<any> => {
    return await httpOperations.put(`/api/v1/sensors/${id}`, data)
}

export const deleteModbusRegister = async (id: number): Promise<any> => {
    return await httpOperations.delete(`/api/v1/sensors/${id}`)
}

export const getHealthStatus = async (): Promise<any> => {
    return await httpOperations.get('/api/v1/health/status', undefined, { meta: { loading: false } })
}

export const getAuditLogs = async (params?: any): Promise<any> => {
    return await httpOperations.get('/api/v1/audit-logs', params)
}

export const getModbusRecords = async (params?: any): Promise<any> => {
    return await httpOperations.get('/api/v1/sensor-histories', params)
}

export const getRegisterTrend = async (registerId: number, params?: any): Promise<any> => {
    return await httpOperations.get(`/api/v1/sensors/trend/${registerId}`, params)
}

export const writeInitialValuesToPlc = async (): Promise<any> => {
    return await httpOperations.post('/api/v1/write-initial-values')
}

export const writeSettingValuesToPlc = async (): Promise<any> => {
    return await httpOperations.post('/api/v1/write-setting-values')
}