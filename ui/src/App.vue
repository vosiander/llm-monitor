<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { ref, provide, onMounted, inject } from 'vue'

const loading = ref(false)
provide('refreshState', { loading })

const llmmonitor = inject('llmmonitor')
const litellmStatus = ref({
  configured: false,
  available: false,
  url: null
})

onMounted(async () => {
  try {
    const response = await llmmonitor.axios.get('/llmm/litellm/status')
    litellmStatus.value = response.data
  } catch (error) {
    console.error('Failed to fetch LiteLLM status:', error)
  }
})
</script>

<template>
  <div class="container">
    <header>
      <b-navbar>
        <template #brand>
            <b-navbar-item tag="router-link" :to="{ path: '/' }"><img src="/logo.jpeg" alt="llm-monitor" /></b-navbar-item>
        </template>
        <template #start>
            <b-navbar-item tag="router-link" :to="{ path: '/' }">Home</b-navbar-item>
            <b-navbar-item tag="router-link" :to="{ path: '/about' }">About</b-navbar-item>
        </template>
        <template #end>
            <b-navbar-item v-if="litellmStatus.configured" class="litellm-status">
                <span class="tag" :class="litellmStatus.available ? 'is-success' : 'is-warning'">
                    <span class="icon">
                        <v-icon :name="litellmStatus.available ? 'fa-check-circle' : 'fa-exclamation-triangle'" />
                    </span>
                    <span>LiteLLM {{ litellmStatus.available ? 'Connected' : 'Unavailable' }}</span>
                </span>
            </b-navbar-item>
        </template>
    </b-navbar>
    </header>

    <RouterView />
  </div>
</template>

<style scoped>
.navbar {
  margin-bottom: 2rem;
}

.litellm-status .tag {
  font-size: 0.875rem;
  padding: 0.5rem 0.75rem;
}

.litellm-status .icon {
  margin-right: 0.25rem;
}
</style>
