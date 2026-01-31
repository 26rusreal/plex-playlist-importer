<template>
  <div class="app">
    <header class="header">
      <div class="container header-content">
        <router-link to="/" class="logo">
          <div class="logo-icon">P</div>
          <span class="logo-text">Playlist Importer</span>
        </router-link>
        <nav class="nav">
          <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
            Playlists
          </router-link>
          <router-link to="/settings" class="nav-link" :class="{ active: $route.path === '/settings' }">
            Settings
          </router-link>
        </nav>
      </div>
    </header>
    
    <main class="main">
      <div class="container">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>
