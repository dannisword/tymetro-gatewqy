<script setup>
import { ref } from "vue";
import { RouterView } from "vue-router";
import AccountDropdown from "./AccountDropdown.vue";

const sidebarOpen = ref(false);

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value;
};
</script>
<template>
  <div class="flex flex-col min-h-screen">
    <!-- Header -->
    <header
      class="bg-blue-600/60 text-white p-4 flex justify-between items-center"
    >
      <h1 class="text-lg font-bold">My App</h1>
      <button
        @click="toggleSidebar"
        class="sm:hidden bg-blue-500 px-3 py-1 rounded"
      >
        Menu
      </button>
    </header>

    <div class="flex flex-1 relative">
      <!-- Sidebar -->
      <aside
        :class="[
          'bg-gray-800 text-white w-64 p-4 sm:block',
          sidebarOpen ? 'block absolute z-50 h-screen top-0 left-0' : 'hidden',
        ]"
      >
        <nav class="space-y-2">
          <a href="/dashboard" class="block px-2 py-1 rounded hover:bg-gray-700"
            >Dashboard</a
          >
          <a href="/document-templates" class="block px-2 py-1 rounded hover:bg-gray-700"
            >Profile</a
          >
          <a href="#" class="block px-2 py-1 rounded hover:bg-gray-700"
            >Settings</a
          >
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="flex-1 p-6 bg-gray-100">
        <h2 class="text-2xl font-bold mb-4">Main Content</h2>

        <router-view />
      </main>
    </div>
  </div>
</template>
