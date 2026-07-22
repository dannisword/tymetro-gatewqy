import { reactive, computed } from 'vue'

/**
 * Sidebar 控制
 * mode: 'auto' | 'manual'
 *  - auto   => 視窗寬度 < 1024px 自動收合
 *  - manual => 使用者自行點擊開關
 */
const state = reactive({
  mode: 'auto' as 'auto' | 'manual',
  collapsed: false,
})

function setAutoByViewport(width?: number) {
  const w = width ?? window.innerWidth
  state.collapsed = w < 1024
}

export function useSider() {
  const isAuto = computed(() => state.mode === 'auto')
  const collapsed = computed(() => state.collapsed)

  /** 切換展開/收合 */
  function toggle() {
    state.collapsed = !state.collapsed
  }

  /** 改變模式 */
  function setMode(m: 'auto' | 'manual') {
    state.mode = m
    if (m === 'auto') setAutoByViewport()
  }

  /** 綁定 resize event (只在 auto 模式作用) */
  function attachAutoResize() {
    const handler = () => state.mode === 'auto' && setAutoByViewport()
    window.addEventListener('resize', handler)
    handler() // 初始化
    return () => window.removeEventListener('resize', handler)
  }

  return {
    state,
    isAuto,
    collapsed,
    toggle,
    setMode,
    attachAutoResize,
  }
}
