<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { ref, provide } from 'vue'

const loading = ref(false)
provide('refreshState', { loading })
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
    </b-navbar>
    </header>

    <RouterView />
  </div>
</template>

<style scoped>
.navbar {
  margin-bottom: 2rem;
}
</style>
