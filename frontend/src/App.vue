<template>
  <div class="app">
    <header class="header">
      <div class="container header-content">
        <router-link to="/" class="logo">
          <img src="/playlist-icon.png" alt="Logo" class="logo-img" />
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

<style scoped>
.logo-img {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  transition: all 0.3s ease;
  filter: drop-shadow(0 0 8px rgba(229, 160, 13, 0.4));
}

.logo:hover .logo-img {
  transform: scale(1.1) rotate(-5deg);
  filter: drop-shadow(0 0 16px rgba(229, 160, 13, 0.7));
}
</style>
