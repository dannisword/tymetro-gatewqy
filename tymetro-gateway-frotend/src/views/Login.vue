<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAppStore } from '../store/useAppStore'
import httpOperations from '../utils/http-operations'

const router = useRouter()

onMounted(() => {})
onUnmounted(() => {})
const form = reactive({
  username: 'admin',
  password: 'admin123',
  remember: true,
})

const showPassword = ref(false)

const onSubmit = async () => {
  try {
    const response: any = await login()
    if (response?.data) {
      await useAppStore().login(response.data)
      const redirect = router.currentRoute.value.query.redirect as string
      router.push(redirect || '/dashboard').catch((err) => console.error('Navigation error:', err))
    }
  } catch (error) {
    console.error('Login failed:', error)
  }
}

const onBack = () => {
  router.back()
}

async function login() {
  try {
    const url = '/api/v1/users/login'
    const response = await httpOperations.post(url, {
      account: form.username,
      password: form.password,
    })

    return response
  } catch (error) {}
}
</script>

<template>
  <div class="min-h-screen grid grid-cols-1 lg:grid-cols-2">
    <section class="relative bg-white left-login-section dark:bg-teal-500">
      <div class="min-h-screen flex items-center justify-center p-8">
        <div class="w-full max-w-md">
          <div class="flex items-center justify-center gap-1 pb-2">
            <img class="max-w-[30px] w-full" src="../assets/logo.png" alt="illustration" />
            <h2 class="text-center text-2xl font-bold text-slate-800 dark:text-slate-100">
              桃園捷運系統
            </h2>
          </div>

          <form @submit.prevent="onSubmit" class="space-y-4">
            <div class="space-y-1">
              <label class="block text-sm text-slate-600 dark:text-slate-300">UserName</label>
              <input
                v-model="form.username"
                type="text"
                placeholder="admin or test"
                class="w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:bg-primary-500"
              />
            </div>

            <div class="space-y-1">
              <label class="block text-sm text-slate-600 dark:text-slate-300">Password</label>
              <input
                v-model="form.password"
                type="password"
                placeholder="admin or test"
                class="w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:bg-primary-500"
              />
            </div>

            <div class="flex items-center justify-between">
              <label
                class="inline-flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300"
              >
                <input
                  v-model="form.remember"
                  type="checkbox"
                  class="h-4 w-4 rounded border-slate-300 text-primary-500 focus:text-primary-500"
                />
                Remember me
              </label>
              <a href="#" class="text-sm text-primary-600 hover:underline">forget password</a>
            </div>

            <button
              type="submit"
              class="w-full rounded bg-primary-500 px-4 py-2 text-white hover:bg-primary-500 transition"
            >
              Login
            </button>
          </form>
        </div>
      </div>
    </section>
    <section class="hidden lg:flex flex-col justify-between">
      <div class="flex-1 flex relative min-h-0 overflow-hidden justify-end items-center">
        <img
          class="absolute inset-0 w-full h-full object-cover object-left"
          src="../assets/erp-2.png"
          alt="illustration"
        />
      </div>
    </section>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');

.left-login-section {
  background: url('../assets/left-2.png') no-repeat right center;
  background-size: cover;
}
</style>
