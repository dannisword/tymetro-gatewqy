import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePermissionStore = defineStore('usePermissionStore', () => {
  // 假設角色權限清單
  const roles = ref<string[]>([])
  const permissions = ref<string[]>([])

  function login() {
    
  }
  /** 設定角色 */
  function setRoles(newRoles: string[]) {
    roles.value = newRoles
  }

  /** 設定權限 */
  function setPermissions(newPermissions: string[]) {
    permissions.value = newPermissions
  }

  /** 檢查角色是否包含 */
  function hasRole(role: string): boolean {
    return roles.value.includes(role)
  }

  /** 檢查是否有某個權限 */
  function hasPermission(permission: string): boolean {
    return permissions.value.includes(permission)
  }

  return {
    roles,
    permissions,
    setRoles,
    setPermissions,
    hasRole,
    hasPermission,
  }
})