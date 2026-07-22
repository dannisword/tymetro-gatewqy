// src/composables/useTheme.ts
import { ref, watch } from 'vue'
import { themeConfig } from '../config/ui-config'

const isDark = ref(themeConfig.defaultTheme === 'dark')

watch(isDark, (val) => {
    const root = document.documentElement
    root.classList.toggle('dark', val)
    localStorage.setItem('theme', val ? 'dark' : 'light')
})

export function useTheme() {
    const toggleTheme = () => {
        isDark.value = !isDark.value
    }

    const setTheme = (mode: 'light' | 'dark') => {
        isDark.value = mode === 'dark'
    }

    const initTheme = () => {
        const saved = localStorage.getItem('theme')
        if (saved) setTheme(saved as 'light' | 'dark')
    }

    return {
        isDark,
        toggleTheme,
        setTheme,
        initTheme,
        themeConfig,
    }
}
