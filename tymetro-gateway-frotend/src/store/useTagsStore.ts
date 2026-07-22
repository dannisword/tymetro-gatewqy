import { defineStore } from 'pinia'
export interface TagItem {
  title: string;
  path: string;
  closable?: boolean;
  keepAlive?: boolean;
}

export const useTagsStore = defineStore('useTagsStore', {
  state: () => ({
    tags: [] as TagItem[],
    activePath: '' as string,
    homePath: '/dashboard',
    homeTitle: 'Dashboard',
  }),
  actions: {
    ensureHome() {
      if (!this.tags.find(t => t.path === this.homePath)) {
        this.tags.unshift({ title: this.homeTitle, path: this.homePath, closable: false })
      }
    },
    add(path: string, title: string, keepAlive: boolean = true) {
      this.activePath = path
      if (!this.tags.find(t => t.path === path)) {
        this.tags.push({ title, path, closable: path !== this.homePath, keepAlive })
      }
      this.ensureHome()
    },
    addByRoute(route: any) {
      const path = route.fullPath
      const title = (route.meta?.title as string) || route.name?.toString() || 'Untitled'
      const keepAlive = route.meta?.keepAlive !== false
      this.add(path, title, keepAlive)
    },
    updateTitle(path: string, title: string) {
      const tag = this.tags.find(t => t.path === path)
      if (tag) {
        tag.title = title
      }
    },
    remove(path: string) {
      const i = this.tags.findIndex(t => t.path === path)
      if (i === -1) return
      this.tags.splice(i, 1)
      if (this.activePath === path) {
        const next = this.tags[i - 1] ?? this.tags[i] ?? this.tags[0]
        this.activePath = next?.path ?? this.homePath
      }
    },
    closeLeft(path: string) {
      const i = this.tags.findIndex(t => t.path === path)
      if (i > 0) this.tags.splice(0, i)
      this.ensureHome()
    },
    closeRight(path: string) {
      const i = this.tags.findIndex(t => t.path === path)
      if (i !== -1) this.tags.splice(i + 1)
    },
    closeOthers(path: string) {
      const target = this.tags.find(t => t.path === path)
      this.tags.splice(0, this.tags.length)
      if (target) this.tags.push(target)
      this.ensureHome()
      this.activePath = path
    },
    closeAll() {
      this.tags = []
      this.ensureHome()
      this.activePath = this.homePath
    },
  },
  persist: {
    key: 'useTagsStore',
    storage: localStorage,
  },
})
